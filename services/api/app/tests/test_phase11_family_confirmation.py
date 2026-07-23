from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.api.v1.call_sessions import (
    request_family_confirmation,
    respond_to_family_confirmation,
)
from app.api.v1.families import add_family_member, create_family
from app.api.v1.seniors import create_senior
from app.core.database import Base, SessionLocal, engine
from app.models import CallSession, FamilyConfirmation, ResponseAction, RiskDecision
from app.schemas import (
    FamilyConfirmationCreate,
    FamilyConfirmationRespond,
    FamilyCreate,
    FamilyMemberCreate,
    SeniorCreate,
)
from app.services.risk_decision_service import RiskDecisionInput, RiskDecisionService


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_not_called_response_recalculates_latest_risk_inputs() -> None:
    db = SessionLocal()
    session, member_id = _create_session_and_member(db)
    risk_service = RiskDecisionService(db)
    risk_service.create(
        session,
        RiskDecisionInput(
            number_mismatch=True,
            speaker_similarity=0.90,
            spoof_probability=0.60,
            content_risk_score=60,
            model_versions_json='{"voice":"mock-0.1"}',
        ),
    )
    db.commit()

    requested = request_family_confirmation(
        session.id,
        FamilyConfirmationCreate(family_member_id=member_id),
        db,
    )
    response = respond_to_family_confirmation(
        requested.confirmation_id,
        FamilyConfirmationRespond(response="NOT_CALLED"),
        db,
    )

    assert response.status == "RESPONDED"
    assert response.risk_score == 80
    assert response.risk_level == "CRITICAL"
    assert response.decision == "BLOCK"
    assert "FAMILY_DENIED_CALL" in response.reason_codes
    decisions = db.query(RiskDecision).order_by(RiskDecision.sequence).all()
    assert [decision.sequence for decision in decisions] == [1, 2]
    assert decisions[-1].speaker_similarity == 0.90
    assert decisions[-1].model_versions_json == '{"voice":"mock-0.1"}'
    assert db.query(ResponseAction).filter_by(risk_decision_id=decisions[-1].id).count() == 1
    db.close()


def test_called_response_can_lower_risk() -> None:
    db = SessionLocal()
    session, member_id = _create_session_and_member(db)
    RiskDecisionService(db).create(
        session,
        RiskDecisionInput(number_mismatch=True, content_risk_score=40),
    )
    db.commit()
    requested = request_family_confirmation(
        session.id,
        FamilyConfirmationCreate(family_member_id=member_id),
        db,
    )

    response = respond_to_family_confirmation(
        requested.confirmation_id,
        FamilyConfirmationRespond(response="CALLED"),
        db,
    )

    assert response.risk_score == 15
    assert response.risk_level == "LOW"
    assert response.decision == "VERIFY"
    assert "FAMILY_CONFIRMED_CALL" in response.reason_codes
    db.close()


def test_expired_confirmation_cannot_change_decision() -> None:
    db = SessionLocal()
    session, member_id = _create_session_and_member(db)
    RiskDecisionService(db).create(session, RiskDecisionInput(number_mismatch=True))
    confirmation = FamilyConfirmation(
        call_session_id=session.id,
        family_member_id=member_id,
        status="PENDING",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db.add(confirmation)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        respond_to_family_confirmation(
            confirmation.id,
            FamilyConfirmationRespond(response="NOT_CALLED"),
            db,
        )

    assert exc_info.value.status_code == 409
    assert db.get(FamilyConfirmation, confirmation.id).status == "EXPIRED"
    assert db.query(RiskDecision).count() == 1
    db.close()


def _create_session_and_member(db) -> tuple[CallSession, str]:
    family = create_family(FamilyCreate(name="가족 확인 테스트"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="딸", relation="DAUGHTER", phone_number="01011112222"),
        db,
    )
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    session = CallSession(
        senior_id=senior.id,
        caller_number_hash="unknown-hash",
        caller_number_last4="9999",
        family_number_matched=False,
        suspected=True,
        status="NUMBER_CHECKED",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, member.id
