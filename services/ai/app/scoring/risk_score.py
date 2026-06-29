def calculate_final_risk_score(
    *,
    number_risk: int,
    speaker_mismatch: bool,
    spoof_probability: float,
    text_risk_score: int,
    text_reason_codes: list[str],
) -> dict[str, object]:
    score = number_risk
    reasons: list[str] = []

    if speaker_mismatch:
        score += 25
        reasons.append("SPEAKER_MISMATCH")

    if spoof_probability >= 0.70:
        score += 25
        reasons.append("SYNTHETIC_VOICE_SUSPECTED")
    elif spoof_probability >= 0.50:
        score += 15
        reasons.append("SYNTHETIC_VOICE_POSSIBLE")

    score += min(text_risk_score, 40)
    reasons.extend(text_reason_codes)
    reasons = list(dict.fromkeys(reasons))
    score = min(score, 100)

    return {
        "risk_score": score,
        "risk_level": risk_level(score),
        "reason_codes": reasons,
    }


def risk_level(score: int) -> str:
    if score >= 81:
        return "CRITICAL"
    if score >= 61:
        return "HIGH"
    if score >= 31:
        return "CAUTION"
    return "LOW"

