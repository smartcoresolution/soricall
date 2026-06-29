import base64
import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceEnrollResult:
    embedding: str
    model_name: str
    model_version: str
    quality_score: float


class AIClient:
    def enroll_voice(self, *, audio_ref: str) -> VoiceEnrollResult:
        digest = hashlib.sha256(audio_ref.encode("utf-8")).digest()
        quality_score = 0.95 if "clean" in audio_ref.lower() else 0.82
        return VoiceEnrollResult(
            embedding=base64.b64encode(digest).decode("ascii"),
            model_name="mock-speaker-verification",
            model_version="0.1.0",
            quality_score=quality_score,
        )

