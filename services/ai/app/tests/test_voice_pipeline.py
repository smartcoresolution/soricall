from app.main import analyze_voice, enroll_voice
from app.pipelines.voice_analysis_pipeline import VoiceAnalysisPipeline
from app.schemas.voice import VoiceAnalyzeRequest, VoiceEnrollRequest


def test_voice_enroll_returns_embedding() -> None:
    result = VoiceAnalysisPipeline().enroll("family-clean-sample.wav")

    assert result.embedding
    assert result.model_name == "mock-speaker-verification"
    assert result.quality_score >= 0.8


def test_voice_analysis_detects_critical_spoof_money_case() -> None:
    pipeline = VoiceAnalysisPipeline()
    enrollment = pipeline.enroll("family-clean-sample.wav")

    result = pipeline.analyze(
        audio_ref="unknown-mismatch-spoof-money-scam.wav",
        enrolled_embedding=enrollment.embedding,
        number_risk=30,
    )

    assert result.risk_level == "CRITICAL"
    assert not result.speaker_matched
    assert result.spoof_probability >= 0.7
    assert "SPEAKER_MISMATCH" in result.reason_codes
    assert "SYNTHETIC_VOICE_SUSPECTED" in result.reason_codes
    assert "MONEY_TRANSFER_REQUEST" in result.reason_codes


def test_voice_analysis_allows_clean_family_case() -> None:
    pipeline = VoiceAnalysisPipeline()
    enrollment = pipeline.enroll("family-clean-sample.wav")

    result = pipeline.analyze(
        audio_ref="family-match-clean.wav",
        enrolled_embedding=enrollment.embedding,
        number_risk=0,
    )

    assert result.speaker_matched
    assert result.spoof_probability < 0.7
    assert result.risk_level in {"LOW", "CAUTION"}


def test_voice_endpoints_can_be_called_directly() -> None:
    enrollment = enroll_voice(VoiceEnrollRequest(audio_ref="family-clean-sample.wav"))
    analysis = analyze_voice(
        VoiceAnalyzeRequest(
            audio_ref="unknown-mismatch-spoof-money-scam.wav",
            enrolled_embedding=enrollment.embedding,
            number_risk=30,
        )
    )

    assert analysis.risk_level == "CRITICAL"
    assert analysis.text

