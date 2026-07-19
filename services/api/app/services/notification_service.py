from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DevicePushToken, EmergencyNotification, Guardian, RiskEvent
from app.services.fcm_service import FcmService


class NotificationService:
    def __init__(
        self,
        db: Session,
        fcm_service: FcmService | None = None,
    ):
        self.db = db
        self.fcm_service = fcm_service or FcmService()

    def notify_guardians_for_risk_event(
        self,
        *,
        risk_event_id: str,
        message: str,
        commit: bool = True,
    ) -> list[EmergencyNotification]:
        risk_event = self.db.get(RiskEvent, risk_event_id)
        if not risk_event:
            raise ValueError("risk event not found")

        guardians = list(
            self.db.scalars(
                select(Guardian).where(
                    Guardian.senior_id == risk_event.senior_id,
                    Guardian.notify_enabled.is_(True),
                )
            )
        )
        notifications: list[EmergencyNotification] = []

        for guardian in guardians:
            tokens = list(
                self.db.scalars(
                    select(DevicePushToken).where(
                        DevicePushToken.guardian_id == guardian.id,
                        DevicePushToken.active.is_(True),
                    )
                )
            )
            sent = False
            for push_token in tokens:
                result = self.fcm_service.send(
                    token=push_token.token,
                    title="가족 사칭 의심 전화",
                    body=message,
                    data={"risk_event_id": risk_event.id, "guardian_id": guardian.id},
                )
                sent = sent or result.sent
            notification = EmergencyNotification(
                risk_event_id=risk_event_id,
                guardian_id=guardian.id,
                status="SENT" if sent else "FAILED",
                message=message,
                sent_at=datetime.now() if sent else None,
            )
            self.db.add(notification)
            notifications.append(notification)

        if commit:
            self.db.commit()
            for notification in notifications:
                self.db.refresh(notification)
        return notifications

    def respond_to_notification(
        self,
        *,
        notification_id: str,
        response: str,
    ) -> EmergencyNotification:
        notification = self.db.get(EmergencyNotification, notification_id)
        if not notification:
            raise ValueError("notification not found")

        notification.response = response
        notification.status = "RESPONDED"
        notification.responded_at = datetime.now()
        self.db.commit()
        self.db.refresh(notification)
        return notification
