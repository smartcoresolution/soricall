import base64
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeakerEmbeddingResult:
    embedding: bytes
    model_name: str
    model_version: str
    quality_score: float


@dataclass(frozen=True)
class SpeakerSimilarityResult:
    similarity: float
    matched: bool
    threshold: float


class SpeakerVerificationAdapter(ABC):
    @abstractmethod
    def create_embedding(self, audio_ref: str) -> SpeakerEmbeddingResult:
        raise NotImplementedError

    @abstractmethod
    def compare(self, audio_ref: str, enrolled_embedding: bytes) -> SpeakerSimilarityResult:
        raise NotImplementedError


class MockSpeakerVerificationAdapter(SpeakerVerificationAdapter):
    threshold = 0.72

    def create_embedding(self, audio_ref: str) -> SpeakerEmbeddingResult:
        digest = hashlib.sha256(audio_ref.encode("utf-8")).digest()
        quality_score = 0.95 if "clean" in audio_ref.lower() else 0.82
        return SpeakerEmbeddingResult(
            embedding=digest,
            model_name="mock-speaker-verification",
            model_version="0.1.0",
            quality_score=quality_score,
        )

    def compare(self, audio_ref: str, enrolled_embedding: bytes) -> SpeakerSimilarityResult:
        lowered = audio_ref.lower()
        if "mismatch" in lowered or "fake" in lowered or "unknown" in lowered:
            similarity = 0.42
        elif "match" in lowered or "family" in lowered:
            similarity = 0.88
        else:
            similarity = _stable_similarity(audio_ref, enrolled_embedding)

        return SpeakerSimilarityResult(
            similarity=similarity,
            matched=similarity >= self.threshold,
            threshold=self.threshold,
        )


def encode_embedding(embedding: bytes) -> str:
    return base64.b64encode(embedding).decode("ascii")


def decode_embedding(embedding: str) -> bytes:
    return base64.b64decode(embedding.encode("ascii"))


def _stable_similarity(audio_ref: str, enrolled_embedding: bytes) -> float:
    digest = hashlib.sha256(audio_ref.encode("utf-8") + enrolled_embedding).digest()
    bucket = digest[0] / 255
    return round(0.55 + bucket * 0.3, 2)

