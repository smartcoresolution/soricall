from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import EmergencyNotification, RiskEvent
from app.schemas import (
    EmergencyConfirmFamilyCallRequest,
    EmergencyNotificationResponse,
    EmergencyNotifyRequest,
    EmergencyNotifyResponse,
    EmergencyRespondRequest,
    EmergencyRespondResponse,
)
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/emergency", tags=["emergency"])


@router.post(
    "/confirm-family-call",
    response_model=EmergencyNotifyResponse,
    status_code=status.HTTP_201_CREATED,
)
def confirm_family_call(
    request: EmergencyConfirmFamilyCallRequest,
    db: DbSession,
) -> EmergencyNotifyResponse:
    risk_event_id = request.risk_event_id
    if not risk_event_id:
        risk_event = RiskEvent(
            senior_id=request.senior_id,
            call_event_id=request.call_event_id,
            event_type="FAMILY_CONFIRM_REQUEST",
            risk_score=70,
            risk_level="HIGH",
            reason_codes="FAMILY_IMPERSONATION_RISK",
            summary=request.message,
        )
        db.add(risk_event)
        db.commit()
        db.refresh(risk_event)
        risk_event_id = risk_event.id

    notifications = NotificationService(db).notify_guardians_for_risk_event(
        risk_event_id=risk_event_id,
        message=request.message,
    )
    return EmergencyNotifyResponse(
        emergency_event_id=risk_event_id,
        notified_guardians=len(notifications),
        status="SENT" if notifications else "NO_GUARDIANS",
    )


@router.post("/notify", response_model=EmergencyNotifyResponse, status_code=status.HTTP_201_CREATED)
def notify_guardians(request: EmergencyNotifyRequest, db: DbSession) -> EmergencyNotifyResponse:
    try:
        notifications = NotificationService(db).notify_guardians_for_risk_event(
            risk_event_id=request.risk_event_id,
            message=request.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return EmergencyNotifyResponse(
        emergency_event_id=request.risk_event_id,
        notified_guardians=len(notifications),
        status="SENT" if notifications else "NO_GUARDIANS",
    )


@router.post("/respond", response_model=EmergencyRespondResponse)
def respond_to_emergency(
    request: EmergencyRespondRequest,
    db: DbSession,
) -> EmergencyRespondResponse:
    try:
        notification = NotificationService(db).respond_to_notification(
            notification_id=request.notification_id,
            response=request.response,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return EmergencyRespondResponse(
        notification_id=notification.id,
        status=notification.status,
        response=notification.response or "UNKNOWN",
    )


@router.get("/notifications", response_model=list[EmergencyNotificationResponse])
def list_notifications(
    db: DbSession,
    risk_event_id: str | None = None,
) -> list[EmergencyNotification]:
    statement = select(EmergencyNotification)
    if risk_event_id:
        statement = statement.where(EmergencyNotification.risk_event_id == risk_event_id)
    return list(db.scalars(statement))

