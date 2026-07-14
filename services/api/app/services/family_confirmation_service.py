from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CallSession,
    FamilyConfirmation,
    FamilyMember,
    Guardian,
    DevicePushToken,
    PushDelivery,
    ResponseAction,
    RiskDecision,
    Senior,
)
from app.services.risk_decision_service import RiskDecisionInput, RiskDecisionService
from app.services.fcm_service import FcmService


@dataclass(frozen=True)
class FamilyConfirmationResult:
    confirmation: FamilyConfirmation
    risk_decision: RiskDecision
    response_action: ResponseAction
    reason_codes: list[str]


class FamilyConfirmationService:
    def __init__(self, db: Session, fcm_service: FcmService | None = None):
        self.db = db
        self.fcm_service = fcm_service or FcmService()

    def request(
        self,
        *,
        call_session_id: str,
        family_member_id: str | None,
        guardian_id: str | None,
        channel: str,
        expires_in_seconds: int,
    ) -> FamilyConfirmation:
        session = self.db.get(CallSession, call_session_id)
        if not session:
            raise ValueError("call session not found")
        if family_member_id is None and guardian_id is None:
            raise ValueError("family member or guardian is required")

        senior = self.db.get(Senior, session.senior_id)
        if not senior:
            raise ValueError("senior not found")
        if family_member_id is not None:
            member = self.db.get(FamilyMember, family_member_id)
            if not member or member.family_id != senior.family_id:
                raise ValueError("family member does not belong to call session family")
        if guardian_id is not None:
            guardian = self.db.get(Guardian, guardian_id)
            if not guardian or guardian.senior_id != senior.id:
                raise ValueError("guardian does not belong to call session senior")

        now = datetime.now(timezone.utc)
        confirmation = FamilyConfirmation(
            call_session_id=session.id,
            family_member_id=family_member_id,
            guardian_id=guardian_id,
            channel=channel,
            status="PENDING",
            requested_at=now,
            expires_at=now + timedelta(seconds=expires_in_seconds),
        )
        session.status = "AWAITING_FAMILY_CONFIRMATION"
        self.db.add(confirmation)
        self.db.flush()
        if guardian_id:
            tokens = self.db.scalars(select(DevicePushToken).where(DevicePushToken.guardian_id == guardian_id, DevicePushToken.active.is_(True))).all()
            for push_token in tokens:
                result = self.fcm_service.send(
                    token=push_token.token,
                    title="가족 통화 확인 요청",
                    body="지금 어르신께 전화하셨나요?",
                    data={"confirmation_id": confirmation.id, "call_session_id": session.id},
                )
                self.db.add(PushDelivery(
                    confirmation_id=confirmation.id,
                    push_token_id=push_token.id,
                    status="SENT" if result.sent else "FAILED",
                    attempt_count=1,
                    provider_message_id=result.message_id,
                    error_message=result.error,
                    sent_at=now if result.sent else None,
                ))
        self.db.commit()
        self.db.refresh(confirmation)
        return confirmation

    def respond(self, *, confirmation_id: str, response: str) -> FamilyConfirmationResult:
        confirmation = self.db.get(FamilyConfirmation, confirmation_id)
        if not confirmation:
            raise ValueError("family confirmation not found")
        if confirmation.status == "RESPONDED":
            raise ValueError("family confirmation already responded")
        if confirmation.status == "EXPIRED" or self._is_expired(confirmation):
            confirmation.status = "EXPIRED"
            self.db.commit()
            raise ValueError("family confirmation expired")

        session = self.db.get(CallSession, confirmation.call_session_id)
        if not session:
            raise ValueError("call session not found")
        latest = self.db.scalar(
            select(RiskDecision)
            .where(RiskDecision.call_session_id == session.id)
            .order_by(RiskDecision.sequence.desc())
            .limit(1)
        )
        if not latest:
            raise ValueError("risk decision not found")

        now = datetime.now(timezone.utc)
        confirmation.response = response
        confirmation.status = "RESPONDED"
        confirmation.responded_at = now

        risk_service = RiskDecisionService(self.db)
        decision = risk_service.create(
            session,
            RiskDecisionInput(
                number_mismatch=latest.number_mismatch,
                speaker_similarity=latest.speaker_similarity,
                spoof_probability=latest.spoof_probability,
                content_risk_score=latest.content_risk_score,
                family_response=response,
                face_match_score=latest.face_match_score,
                model_versions_json=latest.model_versions_json,
                voice_profile_id=latest.voice_profile_id,
                transcript=latest.transcript,
                transcript_language=latest.transcript_language,
                transcript_confidence=latest.transcript_confidence,
            ),
        )
        action = ResponseAction(
            call_session_id=session.id,
            risk_decision_id=decision.id,
            action=decision.decision,
            status="PENDING",
        )
        self.db.add(action)
        session.status = "FAMILY_CONFIRMATION_RECEIVED"
        self.db.commit()
        self.db.refresh(confirmation)
        self.db.refresh(decision)
        self.db.refresh(action)
        return FamilyConfirmationResult(
            confirmation=confirmation,
            risk_decision=decision,
            response_action=action,
            reason_codes=risk_service.reason_codes(decision),
        )

    @staticmethod
    def _is_expired(confirmation: FamilyConfirmation) -> bool:
        if confirmation.expires_at is None:
            return False
        expires_at = confirmation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= datetime.now(timezone.utc)
