from pydantic import BaseModel, Field


class VoiceEnrollRequest(BaseModel):
    audio_ref: str = Field(min_length=1)


class VoiceEnrollResponse(BaseModel):
    embedding: str
    model_name: str
    model_version: str
    quality_score: float


class VoiceAnalyzeRequest(BaseModel):
    audio_ref: str = Field(min_length=1)
    enrolled_embedding: str = Field(min_length=1)
    number_risk: int = Field(default=0, ge=0, le=100)
    analysis_mode: str = "POST_CALL_SAMPLE"


class VoiceAnalyzeResponse(BaseModel):
    speaker_similarity: float
    speaker_matched: bool
    spoof_probability: float
    text: str
    language: str
    text_confidence: float
    content_risk_score: int
    content_reason_codes: list[str]
    risk_score: int
    risk_level: str
    reason_codes: list[str]
    message_for_senior: str
    model_version: str = "mock-pipeline-0.1.0"
