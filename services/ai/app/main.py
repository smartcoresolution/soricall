from fastapi import FastAPI

from app.adapters.nlp_risk import RuleBasedNLPRiskAdapter
from app.core.config import get_settings
from app.pipelines.voice_analysis_pipeline import VoiceAnalysisPipeline
from app.schemas.risk import TextAnalyzeRequest, TextAnalyzeResponse
from app.schemas.voice import (
    VoiceAnalyzeRequest,
    VoiceAnalyzeResponse,
    VoiceEnrollRequest,
    VoiceEnrollResponse,
)


settings = get_settings()
nlp_risk_adapter = RuleBasedNLPRiskAdapter()
voice_pipeline = VoiceAnalysisPipeline(nlp_adapter=nlp_risk_adapter)

app = FastAPI(
    title="SoriCall AI",
    description="Mock AI analysis service for 안심소리 가족콜 / SoriCall.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/v1/text/analyze", response_model=TextAnalyzeResponse, tags=["analysis"])
def analyze_text(request: TextAnalyzeRequest) -> TextAnalyzeResponse:
    result = nlp_risk_adapter.analyze_text(request.text)
    return TextAnalyzeResponse(
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        reason_codes=result.reason_codes,
        detected_keywords=result.detected_keywords,
        summary=result.summary,
    )


@app.post("/v1/voice/enroll", response_model=VoiceEnrollResponse, tags=["voice"])
def enroll_voice(request: VoiceEnrollRequest) -> VoiceEnrollResponse:
    result = voice_pipeline.enroll(request.audio_ref)
    return VoiceEnrollResponse(
        embedding=result.embedding,
        model_name=result.model_name,
        model_version=result.model_version,
        quality_score=result.quality_score,
    )


@app.post("/v1/voice/analyze", response_model=VoiceAnalyzeResponse, tags=["voice"])
def analyze_voice(request: VoiceAnalyzeRequest) -> VoiceAnalyzeResponse:
    result = voice_pipeline.analyze(
        audio_ref=request.audio_ref,
        enrolled_embedding=request.enrolled_embedding,
        number_risk=request.number_risk,
    )
    return VoiceAnalyzeResponse(
        speaker_similarity=result.speaker_similarity,
        speaker_matched=result.speaker_matched,
        spoof_probability=result.spoof_probability,
        text=result.text,
        language=result.language,
        text_confidence=result.text_confidence,
        content_risk_score=result.content_risk_score,
        content_reason_codes=result.content_reason_codes,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        reason_codes=result.reason_codes,
        message_for_senior=result.message_for_senior,
    )
