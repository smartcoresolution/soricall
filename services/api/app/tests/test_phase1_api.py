from app.api.v1.auth import login
from app.api.v1.calls import evaluate_call
from app.api.v1.families import add_family_member, create_family, upsert_safe_word, verify_safe_word
from app.api.v1.risk_events import create_risk_event
from app.api.v1.seniors import add_guardian, create_senior
from app.core.database import Base, SessionLocal, engine
from app.models import SafeWord
from app.schemas import (
    CallEvaluateRequest,
    FamilyCreate,
    FamilyMemberCreate,
    GuardianCreate,
    LoginRequest,
    RiskEventCreate,
    SafeWordUpsert,
    SafeWordVerifyRequest,
    SeniorCreate,
)
from app.tests.factories import register_test_user


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_auth_family_senior_guardian_and_safe_word_flow() -> None:
    db = SessionLocal()
    guardian = register_test_user(db, display_name="보호자")

    logged_in = login(
        LoginRequest(phone_number=guardian.user.phone_number, password="password123"),
        db,
    )
    assert logged_in.access_token

    family = create_family(FamilyCreate(name="김씨 가족", created_by=guardian.user.id), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="아들", relation="SON", phone_number="+821012345678"),
        db,
    )
    assert member.phone_number_last4 == "5678"
    assert member.phone_number is None

    senior = create_senior(
        SeniorCreate(family_id=family.id, name="어머니", phone_number="+821099998888"),
        db,
    )
    linked_guardian = add_guardian(
        senior.id,
        GuardianCreate(user_id=guardian.user.id, relation="DAUGHTER"),
        db,
    )
    assert linked_guardian.notify_enabled is True

    safe_word = upsert_safe_word(
        family.id,
        SafeWordUpsert(word="청포도", hint="과일"),
        db,
    )
    stored_safe_word = db.get(SafeWord, safe_word.id)
    assert stored_safe_word is not None
    assert stored_safe_word.word_hash != "청포도"

    assert verify_safe_word(
        family.id,
        SafeWordVerifyRequest(word="청포도"),
        db,
    ).matched
    assert not verify_safe_word(
        family.id,
        SafeWordVerifyRequest(word="바나나"),
        db,
    ).matched

    db.close()


def test_call_evaluation_and_risk_event_flow() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="박씨 가족"), db)
    add_family_member(
        family.id,
        FamilyMemberCreate(name="딸", relation="DAUGHTER", phone_number="+821011112222"),
        db,
    )
    senior = create_senior(SeniorCreate(family_id=family.id, name="아버지"), db)

    family_call = evaluate_call(
        CallEvaluateRequest(
            senior_id=senior.id,
            phone_number="+821011112222",
            direction="INCOMING",
        ),
        db,
    )
    assert family_call.caller_type == "FAMILY"
    assert family_call.risk_level == "LOW"

    unknown_call = evaluate_call(
        CallEvaluateRequest(
            senior_id=senior.id,
            phone_number="+821055556666",
            direction="INCOMING",
        ),
        db,
    )
    assert unknown_call.caller_type == "UNKNOWN"
    assert "UNKNOWN_NUMBER" in unknown_call.reason_codes

    risk_event = create_risk_event(
        RiskEventCreate(
            senior_id=senior.id,
            call_event_id=unknown_call.call_event_id,
            event_type="SUSPICIOUS_CALL",
            risk_score=unknown_call.risk_score,
            risk_level=unknown_call.risk_level,
            reason_codes=unknown_call.reason_codes,
            summary="모르는 번호 경고",
        ),
        db,
    )
    assert {"UNKNOWN_NUMBER", "FAMILY_IMPERSONATION_RISK"}.issubset(risk_event.reason_codes)

    db.close()
