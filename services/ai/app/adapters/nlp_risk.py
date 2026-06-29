from dataclasses import dataclass


RISK_PATTERNS: dict[str, list[str]] = {
    "MONEY_TRANSFER_REQUEST": ["돈 보내", "송금", "계좌", "입금", "현금", "인출", "이체"],
    "FAMILY_IMPERSONATION": ["엄마 나", "아빠 나", "사고 났어", "납치", "다쳤어", "휴대폰 고장"],
    "KEEP_ON_CALL_PRESSURE": ["전화 끊지 마", "끊으면 안 돼", "계속 통화", "아무에게도 말하지 마"],
    "APP_INSTALL_REQUEST": ["앱 설치", "원격제어", "링크 눌러", "문자 보낸 주소", "보안 앱"],
    "AUTHORITY_IMPERSONATION": ["검찰", "경찰", "금감원", "금융감독원", "수사", "대포통장", "구속"],
    "LOAN_SCAM_PATTERN": ["저금리", "대환대출", "신용등급", "보증료", "상환 계좌"],
}


@dataclass(frozen=True)
class TextRiskResult:
    risk_score: int
    risk_level: str
    reason_codes: list[str]
    detected_keywords: list[str]
    summary: str


class RuleBasedNLPRiskAdapter:
    def analyze_text(self, text: str) -> TextRiskResult:
        reason_codes: list[str] = []
        detected_keywords: list[str] = []

        for reason_code, keywords in RISK_PATTERNS.items():
            matches = [keyword for keyword in keywords if keyword in text]
            if matches:
                reason_codes.append(reason_code)
                detected_keywords.extend(matches)

        score = min(len(reason_codes) * 20 + len(detected_keywords) * 5, 100)
        level = _risk_level(score)
        summary = (
            "보이스피싱 위험 표현이 감지되었습니다."
            if score >= 31
            else "뚜렷한 위험 표현은 감지되지 않았습니다."
        )

        return TextRiskResult(
            risk_score=score,
            risk_level=level,
            reason_codes=reason_codes,
            detected_keywords=detected_keywords,
            summary=summary,
        )


def _risk_level(score: int) -> str:
    if score >= 81:
        return "CRITICAL"
    if score >= 61:
        return "HIGH"
    if score >= 31:
        return "CAUTION"
    return "LOW"

