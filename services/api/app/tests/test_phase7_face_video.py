from app.api.v1.face_video import (
    accept_video_verification,
    create_face_profile,
    create_video_verification,
    list_face_profiles,
    list_video_verifications,
    delete_face_profile,
)
from app.api.v1.families import add_family_member, create_family
from app.api.v1.seniors import create_senior
from app.core.database import Base, SessionLocal, engine
from app.schemas import (
    FaceProfileCreate,
    FamilyCreate,
    FamilyMemberCreate,
    SeniorCreate,
    VideoVerificationAccept,
    VideoVerificationCreate,
)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_face_profile_is_stored_for_family_member() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="얼굴 등록 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="딸", relation="DAUGHTER", phone_number="+821012345678"),
        db,
    )

    profile = create_face_profile(
        FaceProfileCreate(
            family_member_id=member.id,
            display_name="딸 얼굴",
            image_ref="demo://daughter-face",
            consent_accepted=True,
        ),
        db,
    )

    profiles = list_face_profiles(db, family_member_id=member.id)

    assert profile.status == "ACTIVE"
    assert profile.consent_accepted is True
    assert profiles[0].image_ref == "demo://daughter-face"

    db.close()


def test_video_verification_accept_sets_match_result() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="화상 확인 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="아들", relation="SON", phone_number="+821011112222"),
        db,
    )
    senior = create_senior(
        SeniorCreate(family_id=family.id, name="김영희", phone_number="+821099998888"),
        db,
    )

    verification = create_video_verification(
        VideoVerificationCreate(senior_id=senior.id, family_member_id=member.id),
        db,
    )
    accepted = accept_video_verification(
        verification.id,
        VideoVerificationAccept(match_score=91),
        db,
    )

    requests = list_video_verifications(db, senior_id=senior.id)

    assert accepted.status == "ACCEPTED"
    assert accepted.result == "HIGH_MATCH"
    assert requests[0].match_score == 91

    db.close()


def test_face_profile_requires_consent_and_soft_delete_removes_raw_reference() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="얼굴 동의 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="딸", relation="DAUGHTER", phone_number="+821012345679"),
        db,
    )
    profile = create_face_profile(
        FaceProfileCreate(
            family_member_id=member.id,
            display_name="딸 얼굴",
            image_ref="data:image/png;base64,aW1hZ2U=",
            consent_accepted=True,
        ),
        db,
    )
    assert profile.validation_status == "VALIDATED"
    assert profile.size_bytes == 5
    assert profile.image_ref is None
    assert profile.consented_at is not None

    delete_face_profile(profile.id, db)
    db.refresh(profile)
    assert profile.status == "DELETED"
    assert profile.consent_accepted is False
    assert profile.deleted_at is not None
    db.close()
