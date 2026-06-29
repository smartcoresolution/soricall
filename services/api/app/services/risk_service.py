from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_phone_number, phone_last4
from app.models import CallEvent, FamilyMember, RiskEvent, RiskNumber, Senior
from app.services.notification_service import NotificationService


@dataclass(frozen=True)
class RiskEvaluation:
    risk_score: int
    risk_level: str
    caller_type: str
    action_recommended: str
    reason_codes: list[str]
    message_for_senior: str


class RiskService:
    def __init__(self, db: Session):
        self.db = db

    def evaluate_phone_number(
        self,
        *,
        senior_id: str,
        phone_number: str,
        direction: str,
        occurred_at: datetime | None = None,
    ) -> tuple[RiskEvaluation, CallEvent]:
        senior = self.db.get(Senior, senior_id)
        if not senior:
            raise ValueError("senior not found")

        occurred_at = occurred_at or datetime.now()
        phone_hash = hash_phone_number(phone_number)
        is_family = self._is_family_number(senior.family_id, phone_hash)
        risk_number = self._risk_number(phone_hash)
        repeated_count = self._recent_call_count(senior_id, phone_hash, occurred_at)
        evaluation = self._score_number(
            is_family=is_family,
            risk_number=risk_number,
            repeated_count=repeated_count,
            occurred_at=occurred_at,
        )
        call_event = CallEvent(
            senior_id=senior_id,
            phone_number_hash=phone_hash,
            phone_number_last4=phone_last4(phone_number),
            direction=direction,
            caller_type=evaluation.caller_type,
            risk_score=evaluation.risk_score,
            risk_level=evaluation.risk_level,
            action_taken=evaluation.action_recommended,
            occurred_at=occurred_at,
        )
        self.db.add(call_event)
        self.db.flush()

        if evaluation.risk_score >= 61:
            risk_event = RiskEvent(
                senior_id=senior_id,
                call_event_id=call_event.id,
                event_type="SUSPICIOUS_CALL",
                risk_score=evaluation.risk_score,
                risk_level=evaluation.risk_level,
                reason_codes=",".join(evaluation.reason_codes),
                summary=evaluation.message_for_senior,
            )
            self.db.add(risk_event)
            self.db.flush()
            NotificationService(self.db).notify_guardians_for_risk_event(
                risk_event_id=risk_event.id,
                message="부모님이 가족 사칭 의심 전화를 받고 있습니다.",
                commit=False,
            )

        self.db.commit()
        self.db.refresh(call_event)
        return evaluation, call_event

    def _is_family_number(self, family_id: str, phone_hash: str) -> bool:
        return (
            self.db.scalar(
                select(FamilyMember).where(
                    FamilyMember.family_id == family_id,
                    FamilyMember.phone_number_hash == phone_hash,
                )
            )
            is not None
        )

    def _risk_number(self, phone_hash: str) -> RiskNumber | None:
        return self.db.scalar(
            select(RiskNumber).where(
                RiskNumber.phone_number_hash == phone_hash,
                RiskNumber.active.is_(True),
            )
        )

    def _recent_call_count(self, senior_id: str, phone_hash: str, occurred_at: datetime) -> int:
        since = occurred_at - timedelta(hours=1)
        return int(
            self.db.scalar(
                select(func.count(CallEvent.id)).where(
                    CallEvent.senior_id == senior_id,
                    CallEvent.phone_number_hash == phone_hash,
                    CallEvent.occurred_at >= since,
                )
            )
            or 0
        )

    def _score_number(
        self,
        *,
        is_family: bool,
        risk_number: RiskNumber | None,
        repeated_count: int,
        occurred_at: datetime,
    ) -> RiskEvaluation:
        if is_family:
            return RiskEvaluation(
                risk_score=10,
                risk_level="LOW",
                caller_type="FAMILY",
                action_recommended="ALLOW",
                reason_codes=[],
                message_for_senior="등록된 가족 번호입니다.",
            )

        score = 30
        reason_codes = ["UNKNOWN_NUMBER"]
        caller_type = "UNKNOWN"

        if risk_number:
            score = max(score, risk_number.risk_score)
            caller_type = "RISK_NUMBER"
            reason_codes.append("RISK_NUMBER_MATCH")
        else:
            reason_codes.append("FAMILY_IMPERSONATION_RISK")

        if repeated_count >= 2:
            score += 20
            reason_codes.append("REPEATED_CALLS")

        if occurred_at.hour >= 22 or occurred_at.hour < 6:
            score += 15
            reason_codes.append("LATE_NIGHT_CALL")

        score = min(score, 100)
        level = _risk_level(score)
        action = _recommended_action(score)
        message = _message_for_level(level)

        return RiskEvaluation(
            risk_score=score,
            risk_level=level,
            caller_type=caller_type,
            action_recommended=action,
            reason_codes=reason_codes,
            message_for_senior=message,
        )


def _risk_level(score: int) -> str:
    if score >= 81:
        return "CRITICAL"
    if score >= 61:
        return "HIGH"
    if score >= 31:
        return "CAUTION"
    return "LOW"


def _recommended_action(score: int) -> str:
    if score >= 81:
        return "SILENCE_OR_BLOCK_AND_NOTIFY_GUARDIAN"
    if score >= 61:
        return "WARN_AND_NOTIFY_GUARDIAN"
    if score >= 31:
        return "WARN"
    return "ALLOW"


def _message_for_level(level: str) -> str:
    if level == "CRITICAL":
        return "매우 위험한 전화일 수 있습니다. 전화를 끊고 저장된 가족 번호로 다시 확인하세요."
    if level == "HIGH":
        return "위험한 전화일 수 있습니다. 가족 확인 버튼으로 보호자에게 확인하세요."
    if level == "CAUTION":
        return "모르는 번호입니다. 가족이라고 해도 저장된 가족 번호로 다시 확인하세요."
    return "일반 전화로 보입니다."
