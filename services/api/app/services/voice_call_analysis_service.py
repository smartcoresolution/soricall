import json

from sqlalchemy.orm import Session

from app.models import CallSession, ResponseAction, VoiceProfile
from app.services.ai_client import AIClient
from app.services.call_analysis_service import CallAnalysisResult
from app.services.risk_decision_service import RiskDecisionInput, RiskDecisionService


class VoiceCallAnalysisService:
    def __init__(self, db: Session, ai_client: AIClient | None = None):
        self.db = db
        self.ai_client = ai_client or AIClient()

    def analyze(
        self,
        *,
        call_session_id: str,
        voice_profile_id: str,
        audio_ref: str,
    ) -> CallAnalysisResult:
        session = self.db.get(CallSession, call_session_id)
        if not session:
            raise ValueError("call session not found")
        profile = self.db.get(VoiceProfile, voice_profile_id)
        if not profile or profile.status != "ENROLLED" or not profile.embedding:
            raise ValueError("enrolled voice profile not found")

        ai_result = self.ai_client.analyze_voice(
            audio_ref=audio_ref,
            enrolled_embedding=profile.embedding,
            number_risk=20 if not session.family_number_matched else 0,
        )
        risk_service = RiskDecisionService(self.db)
        decision = risk_service.create(
            session,
            RiskDecisionInput(
                number_mismatch=not session.family_number_matched,
                speaker_similarity=ai_result.speaker_similarity,
                spoof_probability=ai_result.spoof_probability,
                content_risk_score=ai_result.content_risk_score,
                model_versions_json=json.dumps(ai_result.model_versions, sort_keys=True),
                additional_reason_codes=ai_result.content_reason_codes,
                voice_profile_id=profile.id,
                transcript=ai_result.text,
                transcript_language=ai_result.language,
                transcript_confidence=ai_result.text_confidence,
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
        return CallAnalysisResult(decision, action, risk_service.reason_codes(decision))
