import pytest
from fastapi import HTTPException

from app.api.v1.families import add_family_member, create_family
from app.api.v1.voice_profiles import (
    add_voice_sample,
    create_voice_profile,
    delete_voice_profile,
    enroll_voice_profile,
    get_voice_profile,
)
from app.core.database import Base, SessionLocal, engine
from app.models import VoiceProfile, VoiceSample
from app.schemas import (
    FamilyCreate,
    FamilyMemberCreate,
    VoiceEnrollRequest,
    VoiceProfileCreate,
    VoiceSampleCreate,
)


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_voice_profile_enrollment_stores_mock_embedding_without_raw_retention() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="음성 등록 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="아들", relation="SON", phone_number="+821012345678"),
        db,
    )

    profile = create_voice_profile(
        VoiceProfileCreate(family_member_id=member.id, display_name="아들 목소리"),
        db,
    )
    assert profile.status == "PENDING"

    sample = add_voice_sample(
        profile.id,
        VoiceSampleCreate(
            audio_ref="family-clean-sample.wav",
            object_key="local/family-clean-sample.wav",
            duration_ms=15000,
            sample_rate=16000,
            mime_type="audio/wav",
        ),
        db,
    )
    assert sample.retained is False
    assert sample.audio_ref is None
    assert sample.object_key is None
    assert sample.validation_status == "DEVELOPMENT_REFERENCE"
    assert sample.deleted_at is not None

    enrolled = enroll_voice_profile(
        profile.id,
        VoiceEnrollRequest(audio_ref="family-clean-sample.wav"),
        db,
    )
    assert enrolled.status == "ENROLLED"
    assert enrolled.embedding_model == "mock-speaker-verification"
    assert enrolled.quality_score is not None

    stored_profile = db.get(VoiceProfile, profile.id)
    assert stored_profile is not None
    assert stored_profile.embedding
    assert stored_profile.embedding_version == "0.1.0"

    stored_sample = db.get(VoiceSample, sample.id)
    assert stored_sample is not None
    assert stored_sample.audio_ref is None
    assert stored_sample.object_key is None

    db.close()


def test_voice_enrollment_rejects_short_or_unsupported_sample() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="음성 검증 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="아들", relation="SON", phone_number="+821033334444"),
        db,
    )
    profile = create_voice_profile(
        VoiceProfileCreate(family_member_id=member.id, display_name="검증 목소리"),
        db,
    )

    with pytest.raises(HTTPException) as too_short:
        add_voice_sample(
            profile.id,
            VoiceSampleCreate(
                audio_ref="data:audio/webm;base64,dGVzdA==",
                duration_ms=5000,
                mime_type="audio/webm",
            ),
            db,
        )
    assert too_short.value.detail == "VOICE_TOO_SHORT"

    with pytest.raises(HTTPException) as unsupported:
        add_voice_sample(
            profile.id,
            VoiceSampleCreate(
                audio_ref="data:text/plain;base64,dGVzdA==",
                duration_ms=15000,
                mime_type="text/plain",
            ),
            db,
        )
    assert unsupported.value.detail == "FILE_UNSUPPORTED"
    db.close()


def test_voice_profile_delete_clears_embedding() -> None:
    db = SessionLocal()
    family = create_family(FamilyCreate(name="음성 삭제 가족"), db)
    member = add_family_member(
        family.id,
        FamilyMemberCreate(name="딸", relation="DAUGHTER", phone_number="+821011112222"),
        db,
    )
    profile = create_voice_profile(
        VoiceProfileCreate(family_member_id=member.id, display_name="딸 목소리"),
        db,
    )
    enroll_voice_profile(profile.id, VoiceEnrollRequest(audio_ref="family-clean-sample.wav"), db)

    delete_voice_profile(profile.id, db)
    deleted = get_voice_profile(profile.id, db)

    assert deleted.status == "DELETED"
    assert deleted.embedding_model is None

    db.close()
