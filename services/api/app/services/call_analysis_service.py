import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import CallSession, ResponseAction, RiskDecision
from app.services.risk_decision_service import RiskDecisionInput, RiskDecisionService


@dataclass(frozen=True)
class CallAnalysisResult:
    risk_decision: RiskDecision
    response_action: ResponseAction
    reason_codes: list[str]


class CallAnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def submit(
        self,
        *,
        call_session_id: str,
        speaker_similarity: float,
        spoof_probability: float,
        content_risk_score: int,
        content_reason_codes: list[str],
        face_match_score: int | None,
        model_versions: dict[str, str],
    ) -> CallAnalysisResult:
        session = self.db.get(CallSession, call_session_id)
        if not session:
            raise ValueError("call session not found")
        if session.status in {"ENDED", "BLOCKED"}:
            raise ValueError("call session is closed")

        risk_service = RiskDecisionService(self.db)
        decision = risk_service.create(
            session,
            RiskDecisionInput(
                number_mismatch=not session.family_number_matched,
                speaker_similarity=speaker_similarity,
                spoof_probability=spoof_probability,
                content_risk_score=content_risk_score,
                face_match_score=face_match_score,
                model_versions_json=json.dumps(model_versions, ensure_ascii=False, sort_keys=True),
                additional_reason_codes=content_reason_codes,
            ),
        )
        action = ResponseAction(
            call_session_id=session.id,
            risk_decision_id=decision.id,
            action=decision.decision,
            status="PENDING",
        )
        self.db.add(action)
        session.status = "ANALYZED"
        self.db.commit()
        self.db.refresh(decision)
        self.db.refresh(action)
        return CallAnalysisResult(
            risk_decision=decision,
            response_action=action,
            reason_codes=risk_service.reason_codes(decision),
        )
