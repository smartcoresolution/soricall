import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.api.v1.families import add_family_member, create_enrollment_invitation
from app.api.v1.media_assets import create_import_session, validate_import_session
from app.api.v1.qr_enrollment import (
    create_qr_challenge,
    register_device_key,
    verify_qr_challenge,
)
from app.core.authorization import current_user_id
from app.core.database import Base, SessionLocal, engine
from app.models import FamilyMember
from app.models import AuditLog
from app.schemas import (
    FamilyMemberCreate,
    MediaImportSessionCreate,
    MediaImportValidate,
    DeviceKeyRegister,
    QrChallengeCreate,
    QrChallengeVerify,
)
from app.api.v1.families import create_family
from app.schemas import FamilyCreate
from app.tests.factories import register_test_user


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _member(db):
    family = create_family(FamilyCreate(name="외부 파일 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="아들", relation="SON", phone_number="01012345678"),
        db,
    )
    return family, member


def test_external_file_is_validated_but_kept_at_trust_d() -> None:
    db = SessionLocal()
    family, member = _member(db)
    session = create_import_session(
        MediaImportSessionCreate(
            family_id=family.id,
            family_member_id=member.id,
            filename="voice.wav",
            mime_type="audio/wav",
        ),
        db,
    )
    validated = validate_import_session(
        session.id,
        MediaImportValidate(data_url="data:audio/wav;base64,UklGRmRhdGF2b2ljZQ=="),
        db,
    )
    assert validated.status == "VALIDATED"
    assert validated.trust_level == "D"
    assert validated.quality_status == "BASIC_VALIDATED"
    db.refresh(member)
    assert member.approval_status == "DRAFT"
    assert member.is_verified is False
    db.close()


def test_qr_invitation_expires_in_five_minutes() -> None:
    db = SessionLocal()
    family, member = _member(db)
    invitation = create_enrollment_invitation(family.id, member.id, db, channel="QR")
    assert invitation.channel == "QR"
    assert f"qr_invitation_id={invitation.id}" in (invitation.enrollment_url or "")
    assert "qr_nonce=" in (invitation.enrollment_url or "")
    assert "?token=" not in (invitation.enrollment_url or "")
    assert 0 < (
        __import__("datetime").datetime.fromisoformat(invitation.expires_at)
        - __import__("datetime").datetime.fromisoformat(invitation.sent_at)
    ).total_seconds() <= 300
    db.close()


def test_qr_challenge_requires_signature_from_registered_device_key() -> None:
    db = SessionLocal()
    user = register_test_user(db, display_name="QR 가족").user
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_der = private_key.public_key().public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    context = current_user_id.set(user.id)
    try:
        device_key = register_device_key(
            DeviceKeyRegister(
                device_id="android-test",
                public_key_der_b64=base64.b64encode(public_der).decode(),
            ),
            db,
        )
    finally:
        current_user_id.reset(context)
    family, member = _member(db)
    invitation = create_enrollment_invitation(family.id, member.id, db, channel="QR")
    query = invitation.enrollment_url or ""
    nonce = query.split("qr_nonce=", 1)[1]
    challenge = create_qr_challenge(
        QrChallengeCreate(
            invitation_id=invitation.id,
            nonce=nonce,
            device_key_id=device_key.id,
        ),
        db,
    )
    message = f"{invitation.id}.{challenge.challenge}".encode()
    signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
    verified = verify_qr_challenge(
        challenge.challenge_id,
        QrChallengeVerify(
            challenge=challenge.challenge,
            signature_b64=base64.b64encode(signature).decode(),
        ),
        db,
    )
    assert verified.verified is True
    try:
        verify_qr_challenge(
            challenge.challenge_id,
            QrChallengeVerify(
                challenge=challenge.challenge,
                signature_b64=base64.b64encode(signature).decode(),
            ),
            db,
        )
        raise AssertionError("replayed challenge should fail")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
    assert db.query(AuditLog).filter_by(action="QR_REPLAY_REJECTED").count() == 1
    db.close()
