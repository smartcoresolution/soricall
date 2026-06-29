from pydantic import BaseModel, Field


class TextAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)


class TextAnalyzeResponse(BaseModel):
    risk_score: int
    risk_level: str
    reason_codes: list[str]
    detected_keywords: list[str]
    summary: str

