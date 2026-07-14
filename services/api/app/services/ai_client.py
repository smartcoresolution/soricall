import base64
import hashlib
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class VoiceEnrollResult:
    embedding: str
    model_name: str
    model_version: str
    quality_score: float


@dataclass(frozen=True)
class VoiceAnalyzeResult:
    speaker_similarity: float
    speaker_matched: bool
    spoof_probability: float
    text: str
    language: str
    text_confidence: float
    content_risk_score: int
    content_reason_codes: list[str]
    model_versions: dict[str, str]


class AIClient:
    def __init__(self, *, base_url: str | None = None, timeout_seconds: float = 10.0):
        self.base_url = (base_url or get_settings().ai_service_url).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def enroll_voice(self, *, audio_ref: str) -> VoiceEnrollResult:
        digest = hashlib.sha256(audio_ref.encode("utf-8")).digest()
        quality_score = 0.95 if "clean" in audio_ref.lower() else 0.82
        return VoiceEnrollResult(
            embedding=base64.b64encode(digest).decode("ascii"),
            model_name="mock-speaker-verification",
            model_version="0.1.0",
            quality_score=quality_score,
        )

    def analyze_voice(
        self,
        *,
        audio_ref: str,
        enrolled_embedding: str,
        number_risk: int,
    ) -> VoiceAnalyzeResult:
        try:
            response = httpx.post(
                f"{self.base_url}/v1/voice/analyze",
                json={
                    "audio_ref": audio_ref,
                    "enrolled_embedding": enrolled_embedding,
                    "number_risk": number_risk,
                    "analysis_mode": "CALL_SESSION",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError("AI voice analysis failed") from exc

        return VoiceAnalyzeResult(
            speaker_similarity=float(data["speaker_similarity"]),
            speaker_matched=bool(data["speaker_matched"]),
            spoof_probability=float(data["spoof_probability"]),
            text=str(data["text"]),
            language=str(data["language"]),
            text_confidence=float(data["text_confidence"]),
            content_risk_score=int(data["content_risk_score"]),
            content_reason_codes=list(data["content_reason_codes"]),
            model_versions={"ai_service": str(data.get("model_version", "0.1.0"))},
        )
