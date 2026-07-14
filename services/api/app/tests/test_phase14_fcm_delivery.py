from app.api.v1.auth import register
from app.api.v1.call_sessions import create_call_session, register_push_token
from app.api.v1.families import create_family
from app.api.v1.seniors import add_guardian, create_senior
from app.core.database import Base, SessionLocal, engine
from app.models import PushDelivery
from app.schemas import (
    CallSessionCreate,
    FamilyCreate,
    GuardianCreate,
    PushTokenRegister,
    RegisterRequest,
    SeniorCreate,
)
from app.services.family_confirmation_service import FamilyConfirmationService
from app.services.fcm_service import PushResult


class SuccessfulFcm:
    def send(self, **kwargs) -> PushResult:
        assert kwargs["token"] == "device-token"
        return PushResult(sent=True, message_id="projects/test/messages/1")


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_family_confirmation_sends_and_records_push() -> None:
    db = SessionLocal()
    user = register(
        RegisterRequest(
            email="push@example.com",
            password="password123",
            display_name="보호자",
            role="GUARDIAN",
        ),
        db,
    ).user
    family = create_family(FamilyCreate(name="푸시 가족"), db)
    senior = create_senior(SeniorCreate(family_id=family.id, name="어르신"), db)
    guardian = add_guardian(senior.id, GuardianCreate(user_id=user.id), db)
    register_push_token(
        guardian.id,
        PushTokenRegister(token="device-token", platform="ANDROID"),
        db,
    )
    session = create_call_session(
        CallSessionCreate(senior_id=senior.id, phone_number="01099998888"),
        db,
    )

    confirmation = FamilyConfirmationService(db, SuccessfulFcm()).request(
        call_session_id=session.call_session_id,
        family_member_id=None,
        guardian_id=guardian.id,
        channel="PUSH",
        expires_in_seconds=300,
    )

    delivery = db.query(PushDelivery).filter_by(confirmation_id=confirmation.id).one()
    assert delivery.status == "SENT"
    assert delivery.attempt_count == 1
    assert delivery.provider_message_id == "projects/test/messages/1"
    assert delivery.sent_at is not None
    db.close()
