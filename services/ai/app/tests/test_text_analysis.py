from app.adapters.nlp_risk import RuleBasedNLPRiskAdapter


def test_text_analysis_detects_risk_patterns() -> None:
    adapter = RuleBasedNLPRiskAdapter()

    result = adapter.analyze_text(
        "엄마 나 사고 났어. 지금 돈 보내줘. 전화 끊지 마."
    )

    assert result.risk_level in {"HIGH", "CRITICAL"}
    assert "FAMILY_IMPERSONATION" in result.reason_codes
    assert "MONEY_TRANSFER_REQUEST" in result.reason_codes
    assert "KEEP_ON_CALL_PRESSURE" in result.reason_codes
