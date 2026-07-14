from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_phone_number, phone_last4
from app.models import (
    CallSession,
    FamilyMember,
    ResponseAction,
    RiskDecision,
    Senior,
)
from app.services.risk_decision_service import RiskDecisionInput, RiskDecisionService


@dataclass(frozen=True)
class CallSessionCreation:
    call_session: CallSession
    risk_decision: RiskDecision
    response_action: ResponseAction
    reason_codes: list[str]


class CallSessionService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        senior_id: str,
        phone_number: str,
        direction: str,
    ) -> CallSessionCreation:
        senior = self.db.get(Senior, senior_id)
        if not senior:
            raise ValueError("senior not found")

        last4 = phone_last4(phone_number)
        if len(last4) != 4:
            raise ValueError("phone number must contain at least 4 digits")

        number_hash = hash_phone_number(phone_number)
        matched_member = self.db.scalar(
            select(FamilyMember).where(
                FamilyMember.family_id == senior.family_id,
                FamilyMember.phone_number_hash == number_hash,
            )
        )
        family_number_matched = matched_member is not None
        suspected = not family_number_matched

        session = CallSession(
            senior_id=senior_id,
            caller_number_hash=number_hash,
            caller_number_last4=last4,
            direction=direction,
            family_number_matched=family_number_matched,
            matched_family_member_id=matched_member.id if matched_member else None,
            suspected=suspected,
            status="NUMBER_CHECKED",
        )
        self.db.add(session)
        self.db.flush()

        risk_service = RiskDecisionService(self.db)
        risk_decision = risk_service.create(
            session,
            RiskDecisionInput(number_mismatch=not family_number_matched),
        )
        reason_codes = risk_service.reason_codes(risk_decision)

        response_action = ResponseAction(
            call_session_id=session.id,
            risk_decision_id=risk_decision.id,
            action=risk_decision.decision,
            status="PENDING",
        )
        self.db.add(response_action)
        self.db.commit()
        self.db.refresh(session)
        self.db.refresh(risk_decision)
        self.db.refresh(response_action)

        return CallSessionCreation(
            call_session=session,
            risk_decision=risk_decision,
            response_action=response_action,
            reason_codes=reason_codes,
        )
