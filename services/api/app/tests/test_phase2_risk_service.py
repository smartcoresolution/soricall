from datetime import datetime

from app.api.v1.admin import create_risk_number
from app.api.v1.calls import evaluate_call
from app.api.v1.families import add_family_member, create_family
from app.api.v1.seniors import create_senior, get_screening_cache
from app.core.database import Base, SessionLocal, engine
from app.models import RiskEvent
from app.schemas import (
    CallEvaluateRequest,
    FamilyCreate,
    FamilyMemberCreate,
    RiskNumberCreate,
    SeniorCreate,
)
from app.services.risk_service import RiskService


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_risk_number_match_creates_high_risk_event() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="위험번호 테스트 가족"), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    create_risk_number(
        RiskNumberCreate(
            phone_number="+821066660000",
            label="신고된 사칭 번호",
            risk_score=85,
        ),
        db,
    )

    response = evaluate_call(
        CallEvaluateRequest(
            senior_id=senior.id,
            phone_number="+821066660000",
            direction="INCOMING",
        ),
        db,
    )

    assert response.caller_type == "RISK_NUMBER"
    assert response.risk_level == "CRITICAL"
    assert response.action_recommended == "SILENCE_OR_BLOCK_AND_NOTIFY_GUARDIAN"
    assert "RISK_NUMBER_MATCH" in response.reason_codes
    assert db.query(RiskEvent).count() == 1

    db.close()


def test_repeated_late_night_unknown_call_is_high_risk() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="반복전화 테스트 가족"), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    service = RiskService(db)

    for _ in range(3):
        evaluation, _ = service.evaluate_phone_number(
            senior_id=senior.id,
            phone_number="+821055551111",
            direction="INCOMING",
            occurred_at=datetime(2026, 6, 26, 23, 30),
        )

    assert evaluation.risk_level == "HIGH"
    assert "REPEATED_CALLS" in evaluation.reason_codes
    assert "LATE_NIGHT_CALL" in evaluation.reason_codes
    assert db.query(RiskEvent).count() == 1

    db.close()


def test_family_number_stays_low_even_at_night() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="가족번호 테스트 가족"), db)
    add_family_member(
        family.id,
        FamilyMemberCreate(name="아들", relation="SON", phone_number="+821012345678"),
        db,
    )
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)

    evaluation, _ = RiskService(db).evaluate_phone_number(
        senior_id=senior.id,
        phone_number="+821012345678",
        direction="INCOMING",
        occurred_at=datetime(2026, 6, 26, 23, 30),
    )

    assert evaluation.risk_level == "LOW"
    assert evaluation.reason_codes == []
    assert db.query(RiskEvent).count() == 0

    db.close()


def test_screening_cache_contains_only_active_family_and_risk_numbers() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="선별 캐시 가족"), db)
    active = add_family_member(
        family.id,
        FamilyMemberCreate(name="승인 가족", relation="SON", phone_number="+821012345678"),
        db,
    )
    add_family_member(
        family.id,
        FamilyMemberCreate(name="미승인 가족", relation="DAUGHTER", phone_number="+821087654321"),
        db,
    )
    active.approval_status = "ACTIVE"
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    risk = create_risk_number(
        RiskNumberCreate(phone_number="+821066660000", label="위험번호", risk_score=90),
        db,
    )
    db.commit()

    cache = get_screening_cache(senior.id, db)

    assert active.phone_number_hash in cache.family_number_hashes
    assert len(cache.family_number_hashes) == 1
    assert risk.phone_number_hash in cache.risk_number_hashes
    assert cache.version
    db.close()
