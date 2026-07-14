import pytest
from fastapi import HTTPException

from app.api.v1.call_sessions import create_call_session, report_response_action
from app.api.v1.families import add_family_member, create_family
from app.api.v1.seniors import create_senior
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import CallSession, ResponseAction, RiskDecision
from app.schemas import (
    CallSessionCreate,
    FamilyCreate,
    FamilyMemberCreate,
    ResponseActionResult,
    SeniorCreate,
)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_call_session_endpoint_is_registered() -> None:
    operation = app.openapi()["paths"]["/api/v1/call-sessions"]["post"]

    assert operation["responses"]["201"]["description"] == "Successful Response"


def test_registered_family_number_creates_low_risk_session() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="등록 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="딸", relation="DAUGHTER", phone_number="+82 10-1111-2222"),
        db,
    )
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)

    response = create_call_session(
        CallSessionCreate(
            senior_id=senior.id,
            phone_number="+821011112222",
            direction="INCOMING",
        ),
        db,
    )

    assert response.family_number_matched is True
    assert response.matched_family_member_id == member.id
    assert response.suspected is False
    assert response.risk_level == "LOW"
    assert response.decision == "ALLOW"
    assert db.query(CallSession).count() == 1
    assert db.query(RiskDecision).count() == 1
    assert db.query(ResponseAction).count() == 1
    db.close()


def test_unknown_number_creates_suspicious_verification_session() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="미등록 번호 가족"), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)

    response = create_call_session(
        CallSessionCreate(
            senior_id=senior.id,
            phone_number="010-9999-8888",
        ),
        db,
    )

    assert response.family_number_matched is False
    assert response.matched_family_member_id is None
    assert response.suspected is True
    assert response.risk_score == 20
    assert response.risk_level == "LOW"
    assert response.decision == "VERIFY"
    assert response.reason_codes == ["UNKNOWN_NUMBER"]
    db.close()


def test_call_session_rejects_invalid_phone_number() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="유효성 검사 가족"), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)

    with pytest.raises(HTTPException) as exc_info:
        create_call_session(
            CallSessionCreate(senior_id=senior.id, phone_number="+"),
            db,
        )

    assert exc_info.value.status_code == 400
    assert db.query(CallSession).count() == 0
    db.close()


def test_android_can_report_response_action_result() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="단말 실행 결과 가족"), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    session = create_call_session(
        CallSessionCreate(senior_id=senior.id, phone_number="01099998888"),
        db,
    )

    action = report_response_action(
        session.call_session_id,
        session.response_action_id,
        ResponseActionResult(status="EXECUTED"),
        db,
    )

    assert action.status == "EXECUTED"
    assert action.executed_at is not None
    db.close()
