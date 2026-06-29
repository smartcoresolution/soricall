from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AntiSpoofingResult:
    spoof_probability: float
    is_suspicious: bool
    model_name: str
    model_version: str


class AntiSpoofingAdapter(ABC):
    @abstractmethod
    def analyze(self, audio_ref: str) -> AntiSpoofingResult:
        raise NotImplementedError


class MockAntiSpoofingAdapter(AntiSpoofingAdapter):
    def analyze(self, audio_ref: str) -> AntiSpoofingResult:
        lowered = audio_ref.lower()
        if "spoof" in lowered or "synthetic" in lowered or "deepfake" in lowered:
            probability = 0.82
        elif "clean" in lowered or "real" in lowered:
            probability = 0.12
        else:
            probability = 0.38

        return AntiSpoofingResult(
            spoof_probability=probability,
            is_suspicious=probability >= 0.7,
            model_name="mock-anti-spoofing",
            model_version="0.1.0",
        )

