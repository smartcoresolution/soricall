from app.api.v1.call_sessions import analyze_call_voice, create_call_session
from app.api.v1.families import add_family_member, create_family
from app.api.v1.seniors import create_senior
from app.core.database import Base, SessionLocal, engine
from app.models import RiskDecision, VoiceProfile
from app.schemas import (
    CallSessionCreate,
    CallVoiceAnalysisRequest,
    FamilyCreate,
    FamilyMemberCreate,
    SeniorCreate,
)
from app.services.ai_client import AIClient, VoiceAnalyzeResult


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_ai_voice_result_is_saved_and_scored(monkeypatch) -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="AI 연동 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="딸", phone_number="01011112222"),
        db,
    )
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    profile = VoiceProfile(
        family_member_id=member.id,
        display_name="딸 음성",
        status="ENROLLED",
        embedding="encoded-embedding",
        embedding_model="mock-speaker",
        embedding_version="0.1",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    session = create_call_session(
        CallSessionCreate(senior_id=senior.id, phone_number="01099998888"),
        db,
    )

    def fake_analyze_voice(self, **kwargs) -> VoiceAnalyzeResult:
        assert kwargs["enrolled_embedding"] == "encoded-embedding"
        assert kwargs["number_risk"] == 20
        return VoiceAnalyzeResult(
            speaker_similarity=0.91,
            speaker_matched=True,
            spoof_probability=0.80,
            text="엄마 지금 돈 보내줘",
            language="ko",
            text_confidence=0.96,
            content_risk_score=80,
            content_reason_codes=["MONEY_TRANSFER_REQUEST"],
            model_versions={"ai_service": "mock-0.1"},
        )

    monkeypatch.setattr(AIClient, "analyze_voice", fake_analyze_voice)
    response = analyze_call_voice(
        session.call_session_id,
        CallVoiceAnalysisRequest(voice_profile_id=profile.id, audio_ref="incoming-call.wav"),
        db,
    )

    assert response.risk_level == "CRITICAL"
    assert response.decision == "BLOCK"
    assert response.transcript == "엄마 지금 돈 보내줘"
    assert response.speaker_similarity == 0.91
    stored = db.get(RiskDecision, response.risk_decision_id)
    assert stored is not None
    assert stored.voice_profile_id == profile.id
    assert stored.transcript_language == "ko"
    assert "MONEY_TRANSFER_REQUEST" in stored.reason_codes
    db.close()
