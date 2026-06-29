from dataclasses import dataclass

from app.adapters.anti_spoofing import MockAntiSpoofingAdapter
from app.adapters.nlp_risk import RuleBasedNLPRiskAdapter
from app.adapters.speaker_verification import (
    MockSpeakerVerificationAdapter,
    decode_embedding,
    encode_embedding,
)
from app.adapters.stt import MockSTTAdapter
from app.scoring.risk_score import calculate_final_risk_score


@dataclass(frozen=True)
class VoiceEnrollResult:
    embedding: str
    model_name: str
    model_version: str
    quality_score: float


@dataclass(frozen=True)
class VoiceAnalysisResult:
    speaker_similarity: float
    speaker_matched: bool
    spoof_probability: float
    text: str
    language: str
    text_confidence: float
    risk_score: int
    risk_level: str
    reason_codes: list[str]
    message_for_senior: str


class VoiceAnalysisPipeline:
    def __init__(
        self,
        speaker_adapter: MockSpeakerVerificationAdapter | None = None,
        anti_spoofing_adapter: MockAntiSpoofingAdapter | None = None,
        stt_adapter: MockSTTAdapter | None = None,
        nlp_adapter: RuleBasedNLPRiskAdapter | None = None,
    ):
        self.speaker_adapter = speaker_adapter or MockSpeakerVerificationAdapter()
        self.anti_spoofing_adapter = anti_spoofing_adapter or MockAntiSpoofingAdapter()
        self.stt_adapter = stt_adapter or MockSTTAdapter()
        self.nlp_adapter = nlp_adapter or RuleBasedNLPRiskAdapter()

    def enroll(self, audio_ref: str) -> VoiceEnrollResult:
        result = self.speaker_adapter.create_embedding(audio_ref)
        return VoiceEnrollResult(
            embedding=encode_embedding(result.embedding),
            model_name=result.model_name,
            model_version=result.model_version,
            quality_score=result.quality_score,
        )

    def analyze(
        self,
        *,
        audio_ref: str,
        enrolled_embedding: str,
        number_risk: int = 0,
    ) -> VoiceAnalysisResult:
        similarity = self.speaker_adapter.compare(audio_ref, decode_embedding(enrolled_embedding))
        spoof = self.anti_spoofing_adapter.analyze(audio_ref)
        stt = self.stt_adapter.transcribe(audio_ref)
        text_risk = self.nlp_adapter.analyze_text(stt.text)
        final_score = calculate_final_risk_score(
            number_risk=number_risk,
            speaker_mismatch=not similarity.matched,
            spoof_probability=spoof.spoof_probability,
            text_risk_score=text_risk.risk_score,
            text_reason_codes=text_risk.reason_codes,
        )

        return VoiceAnalysisResult(
            speaker_similarity=similarity.similarity,
            speaker_matched=similarity.matched,
            spoof_probability=spoof.spoof_probability,
            text=stt.text,
            language=stt.language,
            text_confidence=stt.confidence,
            risk_score=int(final_score["risk_score"]),
            risk_level=str(final_score["risk_level"]),
            reason_codes=list(final_score["reason_codes"]),
            message_for_senior=_message_for_level(str(final_score["risk_level"])),
        )


def _message_for_level(level: str) -> str:
    if level == "CRITICAL":
        return "가족 목소리처럼 들려도 AI 조작 가능성이 있습니다. 전화를 끊고 저장된 가족 번호로 다시 확인하세요."
    if level == "HIGH":
        return "위험한 통화일 수 있습니다. 보호자에게 가족 확인을 요청하세요."
    if level == "CAUTION":
        return "주의가 필요합니다. 송금이나 앱 설치 요청은 반드시 가족에게 다시 확인하세요."
    return "뚜렷한 위험 신호는 낮습니다."

