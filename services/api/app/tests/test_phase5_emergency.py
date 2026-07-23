from app.api.v1.admin import create_risk_number
from app.api.v1.emergency import confirm_family_call, list_notifications, respond_to_emergency
from app.api.v1.families import create_family
from app.api.v1.seniors import add_guardian, create_senior
from app.core.database import Base, SessionLocal, engine
from app.models import EmergencyNotification, RiskEvent
from app.schemas import (
    EmergencyConfirmFamilyCallRequest,
    EmergencyRespondRequest,
    FamilyCreate,
    GuardianCreate,
    RiskNumberCreate,
    SeniorCreate,
)
from app.services.risk_service import RiskService
from app.tests.factories import register_test_user


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_confirm_family_call_notifies_guardian_and_saves_response() -> None:
    db = SessionLocal()
    senior_id = _create_senior_with_guardian(db)

    notification_result = confirm_family_call(
        EmergencyConfirmFamilyCallRequest(
            senior_id=senior_id,
            message="가족 사칭 의심 전화입니다.",
        ),
        db,
    )

    assert notification_result.notified_guardians == 1
    # No device token is registered in this fixture, so the notification is
    # persisted but correctly reported as an external delivery failure.
    assert notification_result.status == "FAILED"

    notifications = list_notifications(db, risk_event_id=notification_result.emergency_event_id)
    assert len(notifications) == 1
    assert notifications[0].status == "FAILED"

    response = respond_to_emergency(
        EmergencyRespondRequest(notification_id=notifications[0].id, response="NOT_ME"),
        db,
    )
    assert response.status == "RESPONDED"
    assert response.response == "NOT_ME"

    db.close()


def test_high_risk_call_automatically_creates_guardian_notification() -> None:
    db = SessionLocal()
    senior_id = _create_senior_with_guardian(db)
    create_risk_number(
        RiskNumberCreate(phone_number="+821077770000", label="신고 번호", risk_score=90),
        db,
    )

    evaluation, _ = RiskService(db).evaluate_phone_number(
        senior_id=senior_id,
        phone_number="+821077770000",
        direction="INCOMING",
    )

    assert evaluation.risk_level == "CRITICAL"
    assert db.query(RiskEvent).count() == 1
    assert db.query(EmergencyNotification).count() == 1

    db.close()


def _create_senior_with_guardian(db) -> str:
    guardian_user = register_test_user(db, display_name="보호자")
    family = create_family(FamilyCreate(name="긴급 알림 가족"), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    add_guardian(
        senior.id,
        GuardianCreate(user_id=guardian_user.user.id, relation="DAUGHTER"),
        db,
    )
    return senior.id
