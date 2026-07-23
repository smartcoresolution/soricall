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
        if get_settings().ai_provider == "remote":
            try:
                response = httpx.post(
                    f"{self.base_url}/v1/voice/enroll",
                    json={"audio_ref": audio_ref},
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise RuntimeError("AI voice enrollment failed") from exc
            model_name = str(data["model_name"])
            if get_settings().app_env == "production" and model_name.startswith("mock-"):
                raise RuntimeError("mock AI model is forbidden in production")
            return VoiceEnrollResult(
                embedding=str(data["embedding"]),
                model_name=model_name,
                model_version=str(data["model_version"]),
                quality_score=float(data["quality_score"]),
            )
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

        model_version = str(data.get("model_version", "unknown"))
        if get_settings().app_env == "production" and model_version.startswith("mock"):
            raise RuntimeError("mock AI model is forbidden in production")

        return VoiceAnalyzeResult(
            speaker_similarity=float(data["speaker_similarity"]),
            speaker_matched=bool(data["speaker_matched"]),
            spoof_probability=float(data["spoof_probability"]),
            text=str(data["text"]),
            language=str(data["language"]),
            text_confidence=float(data["text_confidence"]),
            content_risk_score=int(data["content_risk_score"]),
            content_reason_codes=list(data["content_reason_codes"]),
            model_versions={"ai_service": model_version},
        )
