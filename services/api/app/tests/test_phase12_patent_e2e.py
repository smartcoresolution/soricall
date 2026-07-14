from app.api.v1.call_sessions import (
    create_call_session,
    request_family_confirmation,
    respond_to_family_confirmation,
    submit_call_analysis,
)
from app.api.v1.families import add_family_member, create_family
from app.api.v1.seniors import create_senior
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import CallSession, FamilyConfirmation, ResponseAction, RiskDecision
from app.schemas import (
    CallAnalysisSubmit,
    CallSessionCreate,
    FamilyConfirmationCreate,
    FamilyConfirmationRespond,
    FamilyCreate,
    FamilyMemberCreate,
    SeniorCreate,
)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_patent_simulator_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert "post" in paths["/api/v1/call-sessions/{call_session_id}/analyses"]
    assert "post" in paths["/api/v1/call-sessions/{call_session_id}/family-confirmations"]
    assert "post" in paths["/api/v1/family-confirmations/{confirmation_id}/respond"]


def test_patent_impersonation_flow_reaches_critical_block_through_api_handlers() -> None:
    senior_id, member_id = _seed_family("01011112222")
    db = SessionLocal()
    session = create_call_session(
        CallSessionCreate(
            senior_id=senior_id,
            phone_number="01099998888",
            direction="INCOMING",
        ),
        db,
    )
    assert session.family_number_matched is False
    assert session.decision == "VERIFY"

    analysis = submit_call_analysis(
        session.call_session_id,
        CallAnalysisSubmit(
            speaker_similarity=0.91,
            spoof_probability=0.60,
            content_risk_score=60,
            content_reason_codes=["MONEY_TRANSFER_REQUEST"],
            model_versions={
                "speaker": "mock-speaker-0.1",
                "anti_spoofing": "mock-spoof-0.1",
                "stt": "mock-stt-0.1",
            },
        ),
        db,
    )
    assert analysis.risk_score == 65
    assert analysis.risk_level == "HIGH"
    assert analysis.decision == "RECALL"
    assert "MONEY_TRANSFER_REQUEST" in analysis.reason_codes

    confirmation = request_family_confirmation(
        session.call_session_id,
        FamilyConfirmationCreate(family_member_id=member_id),
        db,
    )
    final = respond_to_family_confirmation(
        confirmation.confirmation_id,
        FamilyConfirmationRespond(response="NOT_CALLED"),
        db,
    )
    assert final.risk_score == 80
    assert final.risk_level == "CRITICAL"
    assert final.decision == "BLOCK"
    assert "FAMILY_DENIED_CALL" in final.reason_codes

    stored_session = db.get(CallSession, session.call_session_id)
    assert stored_session is not None
    assert stored_session.status == "FAMILY_CONFIRMATION_RECEIVED"
    assert db.query(RiskDecision).filter_by(call_session_id=stored_session.id).count() == 3
    assert db.query(ResponseAction).filter_by(call_session_id=stored_session.id).count() == 3
    assert db.query(FamilyConfirmation).filter_by(call_session_id=stored_session.id).count() == 1
    db.close()


def test_registered_family_normal_flow_remains_low_through_api_handlers() -> None:
    senior_id, _ = _seed_family("01011112222")
    db = SessionLocal()
    session = create_call_session(
        CallSessionCreate(senior_id=senior_id, phone_number="010-1111-2222"),
        db,
    )
    assert session.family_number_matched is True

    analysis = submit_call_analysis(
        session.call_session_id,
        CallAnalysisSubmit(
            speaker_similarity=0.94,
            spoof_probability=0.05,
            content_risk_score=0,
            model_versions={"speaker": "mock-speaker-0.1"},
        ),
        db,
    )
    assert analysis.risk_score == 0
    assert analysis.risk_level == "LOW"
    assert analysis.decision == "ALLOW"
    db.close()


def _seed_family(family_phone_number: str) -> tuple[str, str]:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="특허 E2E 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(
            name="딸",
            relation="DAUGHTER",
            phone_number=family_phone_number,
        ),
        db,
    )
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    result = (senior.id, member.id)
    db.close()
    return result
