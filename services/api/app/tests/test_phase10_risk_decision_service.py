import pytest

from app.core.database import Base, SessionLocal, engine
from app.models import CallSession, Family, RiskDecision, Senior
from app.services.risk_decision_service import RiskDecisionInput, RiskDecisionService


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_voice_clone_impersonation_reaches_critical() -> None:
    db = SessionLocal()
    service = RiskDecisionService(db)

    result = service.evaluate(
        RiskDecisionInput(
            number_mismatch=True,
            speaker_similarity=0.91,
            spoof_probability=0.87,
            content_risk_score=100,
            family_response="NOT_CALLED",
        )
    )

    assert result.risk_score == 100
    assert result.risk_level == "CRITICAL"
    assert result.decision == "BLOCK"
    assert "FAMILY_VOICE_SIMILAR_ON_UNKNOWN_NUMBER" in result.reason_codes
    assert "SYNTHETIC_VOICE_SUSPECTED" in result.reason_codes
    assert "FAMILY_DENIED_CALL" in result.reason_codes
    db.close()


def test_normal_registered_family_call_stays_low() -> None:
    db = SessionLocal()
    result = RiskDecisionService(db).evaluate(
        RiskDecisionInput(
            number_mismatch=False,
            speaker_similarity=0.92,
            spoof_probability=0.08,
            content_risk_score=0,
            family_response="CALLED",
            face_match_score=90,
        )
    )

    assert result.risk_score == 0
    assert result.risk_level == "LOW"
    assert result.decision == "ALLOW"
    db.close()


def test_registered_number_is_not_automatically_safe() -> None:
    db = SessionLocal()
    result = RiskDecisionService(db).evaluate(
        RiskDecisionInput(
            number_mismatch=False,
            speaker_similarity=0.30,
            spoof_probability=0.90,
            content_risk_score=90,
        )
    )

    assert result.risk_score == 62
    assert result.risk_level == "HIGH"
    assert result.decision == "RECALL"
    assert "REGISTERED_NUMBER_VOICE_MISMATCH" in result.reason_codes
    db.close()


def test_persisted_recalculation_increments_sequence() -> None:
    db = SessionLocal()
    family = Family(name="재판정 가족")
    db.add(family)
    db.flush()
    senior = Senior(family_id=family.id, name="어르신")
    db.add(senior)
    db.flush()
    session = CallSession(
        senior_id=senior.id,
        caller_number_hash="hash",
        caller_number_last4="1234",
        family_number_matched=False,
        suspected=True,
    )
    db.add(session)
    db.flush()

    service = RiskDecisionService(db)
    first = service.create(session, RiskDecisionInput(number_mismatch=True))
    second = service.create(
        session,
        RiskDecisionInput(number_mismatch=True, family_response="NOT_CALLED"),
    )
    db.commit()

    assert first.sequence == 1
    assert second.sequence == 2
    assert db.query(RiskDecision).count() == 2
    db.close()


def test_invalid_probability_is_rejected() -> None:
    db = SessionLocal()
    with pytest.raises(ValueError, match="spoof_probability"):
        RiskDecisionService(db).evaluate(
            RiskDecisionInput(number_mismatch=True, spoof_probability=1.1)
        )
    db.close()


@pytest.mark.parametrize(
    ("score", "expected_level"),
    [
        (29, "LOW"),
        (30, "CAUTION"),
        (59, "CAUTION"),
        (60, "HIGH"),
        (79, "HIGH"),
        (80, "CRITICAL"),
    ],
)
def test_risk_level_boundaries(score: int, expected_level: str) -> None:
    assert RiskDecisionService._risk_level(score) == expected_level
