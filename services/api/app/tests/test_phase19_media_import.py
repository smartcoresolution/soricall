import pytest
from fastapi import HTTPException

from app.api.v1.families import add_family_member, create_enrollment_invitation
from app.api.v1.media_assets import create_import_session, validate_import_session
from app.core.database import Base, SessionLocal, engine
from app.models import FamilyMember
from app.schemas import (
    FamilyMemberCreate,
    MediaImportSessionCreate,
    MediaImportValidate,
)
from app.api.v1.families import create_family
from app.schemas import FamilyCreate


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
        MediaImportValidate(data_url="data:audio/wav;base64,UklGRmRhdGE="),
        db,
    )
    assert validated.status == "VALIDATED"
    assert validated.trust_level == "D"
    db.refresh(member)
    assert member.approval_status == "REVIEW_REQUIRED"
    assert member.is_verified is False
    db.close()


def test_qr_invitation_expires_in_five_minutes() -> None:
    db = SessionLocal()
    family, member = _member(db)
    invitation = create_enrollment_invitation(family.id, member.id, db, channel="QR")
    assert invitation.channel == "QR"
    assert 0 < (
        __import__("datetime").datetime.fromisoformat(invitation.expires_at)
        - __import__("datetime").datetime.fromisoformat(invitation.sent_at)
    ).total_seconds() <= 300
    db.close()
