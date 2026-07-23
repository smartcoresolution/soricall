from dataclasses import dataclass
from dataclasses import field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CallSession, RiskDecision


@dataclass(frozen=True)
class RiskDecisionInput:
    number_mismatch: bool
    speaker_similarity: float | None = None
    spoof_probability: float | None = None
    content_risk_score: int | None = None
    family_response: str | None = None
    face_match_score: int | None = None
    model_versions_json: str = "{}"
    additional_reason_codes: list[str] = field(default_factory=list)
    voice_profile_id: str | None = None
    transcript: str | None = None
    transcript_language: str | None = None
    transcript_confidence: float | None = None


@dataclass(frozen=True)
class RiskDecisionResult:
    risk_score: int
    risk_level: str
    decision: str
    reason_codes: list[str]


class RiskDecisionService:
    POLICY_VERSION = "patent-v1"

    def __init__(self, db: Session):
        self.db = db

    def evaluate(self, inputs: RiskDecisionInput) -> RiskDecisionResult:
        self._validate(inputs)
        score = 0
        reasons: list[str] = []

        if inputs.number_mismatch:
            score += 20
            reasons.append("UNKNOWN_NUMBER")

        if inputs.speaker_similarity is not None:
            if inputs.number_mismatch and inputs.speaker_similarity >= 0.75:
                score += 15
                reasons.append("FAMILY_VOICE_SIMILAR_ON_UNKNOWN_NUMBER")
            elif not inputs.number_mismatch and inputs.speaker_similarity < 0.55:
                score += 15
                reasons.append("REGISTERED_NUMBER_VOICE_MISMATCH")

        if inputs.spoof_probability is not None:
            if inputs.spoof_probability >= 0.70:
                score += 25
                reasons.append("SYNTHETIC_VOICE_SUSPECTED")
            elif inputs.spoof_probability >= 0.50:
                score += 15
                reasons.append("SYNTHETIC_VOICE_POSSIBLE")

        if inputs.content_risk_score is not None and inputs.content_risk_score > 0:
            score += round(inputs.content_risk_score * 0.25)
            reasons.append("RISKY_CONVERSATION_CONTENT")

        if inputs.family_response == "NOT_CALLED":
            score += 15
            reasons.append("FAMILY_DENIED_CALL")
        elif inputs.family_response == "CALLED":
            score -= 15
            reasons.append("FAMILY_CONFIRMED_CALL")
        elif inputs.family_response == "UNKNOWN":
            score += 5
            reasons.append("FAMILY_CONFIRMATION_UNKNOWN")

        if inputs.face_match_score is not None:
            if inputs.face_match_score >= 80:
                score -= 10
                reasons.append("FACE_MATCH_CONFIRMED")
            elif inputs.face_match_score < 55:
                score += 10
                reasons.append("FACE_MATCH_FAILED")

        reasons.extend(inputs.additional_reason_codes)
        reasons = list(dict.fromkeys(reasons))

        score = max(0, min(score, 100))
        risk_level = self._risk_level(score)
        decision = self._decision(score, number_mismatch=inputs.number_mismatch)
        return RiskDecisionResult(
            risk_score=score,
            risk_level=risk_level,
            decision=decision,
            reason_codes=reasons,
        )

    def create(self, call_session: CallSession, inputs: RiskDecisionInput) -> RiskDecision:
        if call_session.id is None:
            raise ValueError("call session must be persisted before risk decision")

        result = self.evaluate(inputs)
        latest_sequence = self.db.scalar(
            select(func.max(RiskDecision.sequence)).where(
                RiskDecision.call_session_id == call_session.id
            )
        )
        decision = RiskDecision(
            call_session_id=call_session.id,
            sequence=int(latest_sequence or 0) + 1,
            number_mismatch=inputs.number_mismatch,
            speaker_similarity=inputs.speaker_similarity,
            spoof_probability=inputs.spoof_probability,
            content_risk_score=inputs.content_risk_score,
            family_response=inputs.family_response,
            face_match_score=inputs.face_match_score,
            voice_profile_id=inputs.voice_profile_id,
            transcript=inputs.transcript,
            transcript_language=inputs.transcript_language,
            transcript_confidence=inputs.transcript_confidence,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            decision=result.decision,
            reason_codes=",".join(result.reason_codes),
            policy_version=self.POLICY_VERSION,
            model_versions_json=inputs.model_versions_json,
        )
        self.db.add(decision)
        self.db.flush()
        return decision

    @staticmethod
    def reason_codes(decision: RiskDecision) -> list[str]:
        return [code for code in decision.reason_codes.split(",") if code]

    @staticmethod
    def _risk_level(score: int) -> str:
        if score >= 80:
            return "CRITICAL"
        if score >= 60:
            return "HIGH"
        if score >= 30:
            return "CAUTION"
        return "LOW"

    @staticmethod
    def _decision(score: int, *, number_mismatch: bool) -> str:
        if score >= 80:
            return "BLOCK"
        if score >= 60:
            return "RECALL"
        if score >= 30 or number_mismatch:
            return "VERIFY"
        return "ALLOW"

    @staticmethod
    def _validate(inputs: RiskDecisionInput) -> None:
        for field_name in ("speaker_similarity", "spoof_probability"):
            value = getattr(inputs, field_name)
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if inputs.transcript_confidence is not None and not 0 <= inputs.transcript_confidence <= 1:
            raise ValueError("transcript_confidence must be between 0 and 1")
        for field_name in ("content_risk_score", "face_match_score"):
            value = getattr(inputs, field_name)
            if value is not None and not 0 <= value <= 100:
                raise ValueError(f"{field_name} must be between 0 and 100")
        if inputs.family_response not in {None, "CALLED", "NOT_CALLED", "UNKNOWN"}:
            raise ValueError("invalid family response")
