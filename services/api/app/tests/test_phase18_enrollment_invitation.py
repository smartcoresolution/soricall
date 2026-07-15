from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException

from app.api.v1.families import (
    add_family_member,
    complete_enrollment_invitation,
    create_enrollment_invitation,
    create_family,
    resend_enrollment_invitation,
    resolve_enrollment_invitation,
)
from app.core.database import Base, SessionLocal, engine
from app.models import EnrollmentInvitation, FaceProfile, FamilyMember, VoiceProfile
from app.schemas import EnrollmentCompleteRequest, FamilyCreate, FamilyMemberCreate


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _invitation() -> tuple[str, str, str]:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="초대 등록 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="초대받은 딸", relation="DAUGHTER", phone_number="01012345678"),
        db,
    )
    invitation = create_enrollment_invitation(family.id, member.id, db)
    assert invitation.channel == "DEVELOPMENT_LINK"
    token = parse_qs(urlparse(invitation.enrollment_url or "").query)["token"][0]
    result = (token, invitation.id, member.id)
    db.close()
    return result


def test_token_resolves_and_completion_is_persisted() -> None:
    token, invitation_id, member_id = _invitation()
    db = SessionLocal()

    resolved = resolve_enrollment_invitation(token, db)
    assert resolved.family_member_name == "초대받은 딸"
    assert resolved.status == "PENDING"

    completed = complete_enrollment_invitation(
        token,
        EnrollmentCompleteRequest(
            audio_ref="data:audio/webm;base64,dGVzdA==",
            duration_ms=2500,
            face_image_ref="dev-local://face.jpg",
            consent_accepted=True,
        ),
        db,
    )

    assert completed.status == "COMPLETED"
    stored = db.get(EnrollmentInvitation, invitation_id)
    assert stored is not None and stored.completed_at is not None
    assert db.get(FamilyMember, member_id).is_verified is True
    assert db.query(VoiceProfile).filter_by(family_member_id=member_id, status="ENROLLED").count() == 1
    assert db.query(FaceProfile).filter_by(family_member_id=member_id, status="ACTIVE").count() == 1
    db.close()


def test_expired_token_cannot_complete_enrollment() -> None:
    token, invitation_id, _ = _invitation()
    db = SessionLocal()
    invitation = db.get(EnrollmentInvitation, invitation_id)
    invitation.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        complete_enrollment_invitation(
            token,
            EnrollmentCompleteRequest(
                audio_ref="sample.wav",
                duration_ms=1000,
                consent_accepted=True,
            ),
            db,
        )

    assert exc_info.value.status_code == 410
    assert db.get(EnrollmentInvitation, invitation_id).status == "EXPIRED"
    db.close()


def test_resend_invalidates_old_token_and_returns_new_development_link() -> None:
    old_token, invitation_id, _ = _invitation()
    db = SessionLocal()
    invitation = db.get(EnrollmentInvitation, invitation_id)
    resent = resend_enrollment_invitation(invitation.family_id, invitation_id, db)
    new_token = parse_qs(urlparse(resent.enrollment_url or "").query)["token"][0]

    assert new_token != old_token
    assert resent.channel == "DEVELOPMENT_LINK"
    with pytest.raises(HTTPException) as exc_info:
        resolve_enrollment_invitation(old_token, db)
    assert exc_info.value.status_code == 404
    assert resolve_enrollment_invitation(new_token, db).status == "PENDING"
    db.close()


def test_completing_same_invitation_twice_does_not_duplicate_profiles() -> None:
    token, _, member_id = _invitation()
    db = SessionLocal()
    request = EnrollmentCompleteRequest(
        audio_ref="sample.wav",
        duration_ms=1000,
        consent_accepted=True,
    )

    assert complete_enrollment_invitation(token, request, db).status == "COMPLETED"
    assert complete_enrollment_invitation(token, request, db).status == "COMPLETED"
    assert db.query(VoiceProfile).filter_by(family_member_id=member_id).count() == 1
    db.close()
