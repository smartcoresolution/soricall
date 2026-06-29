from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class STTResult:
    text: str
    language: str
    confidence: float


class STTAdapter(ABC):
    @abstractmethod
    def transcribe(self, audio_ref: str) -> STTResult:
        raise NotImplementedError


class MockSTTAdapter(STTAdapter):
    def transcribe(self, audio_ref: str) -> STTResult:
        lowered = audio_ref.lower()
        if "money" in lowered or "scam" in lowered:
            text = "엄마 나 사고 났어 지금 돈 보내줘 전화 끊지 마"
        elif "app" in lowered:
            text = "보안 앱 설치하고 링크 눌러"
        elif "authority" in lowered:
            text = "검찰 수사 중입니다 계좌 확인이 필요합니다"
        else:
            text = "오늘 저녁에 집에 들를게요"

        return STTResult(text=text, language="ko", confidence=0.91)

