from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import VoiceProfile, VoiceSample
from app.schemas import (
    VoiceEnrollRequest,
    VoiceEnrollResponse,
    VoiceProfileCreate,
    VoiceProfileResponse,
    VoiceSampleCreate,
    VoiceSampleResponse,
)
from app.services.voice_profile_service import VoiceProfileService


router = APIRouter(prefix="/voice-profiles", tags=["voice-profiles"])


@router.post("", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
def create_voice_profile(request: VoiceProfileCreate, db: DbSession) -> VoiceProfile:
    try:
        return VoiceProfileService(db).create_profile(
            family_member_id=request.family_member_id,
            display_name=request.display_name,
            consent_id=request.consent_id,
        )
    except ValueError as exc:
        status_code = 404 if str(exc) == "family member not found" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("", response_model=list[VoiceProfileResponse])
def list_voice_profiles(db: DbSession, family_member_id: str | None = None) -> list[VoiceProfile]:
    statement = select(VoiceProfile).where(VoiceProfile.status != "DELETED")
    if family_member_id:
        statement = statement.where(VoiceProfile.family_member_id == family_member_id)
    return list(db.scalars(statement))


@router.get("/{profile_id}", response_model=VoiceProfileResponse)
def get_voice_profile(profile_id: str, db: DbSession) -> VoiceProfile:
    profile = db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="voice profile not found")
    return profile


@router.post(
    "/{profile_id}/samples",
    response_model=VoiceSampleResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_voice_sample(profile_id: str, request: VoiceSampleCreate, db: DbSession) -> VoiceSampleResponse:
    try:
        sample = VoiceProfileService(db).add_sample(
            voice_profile_id=profile_id,
            audio_ref=request.audio_ref,
            object_key=request.object_key,
            duration_ms=request.duration_ms,
            sample_rate=request.sample_rate,
            mime_type=request.mime_type,
            purpose=request.purpose,
        )
    except ValueError as exc:
        status_code = 404 if str(exc) == "voice profile not found" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return VoiceSampleResponse.model_validate(sample)


@router.post("/{profile_id}/enroll", response_model=VoiceEnrollResponse)
def enroll_voice_profile(
    profile_id: str,
    request: VoiceEnrollRequest,
    db: DbSession,
) -> VoiceEnrollResponse:
    try:
        profile = VoiceProfileService(db).enroll(
            voice_profile_id=profile_id,
            audio_ref=request.audio_ref,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return VoiceEnrollResponse(
        id=profile.id,
        status=profile.status,
        embedding_model=profile.embedding_model,
        embedding_version=profile.embedding_version,
        quality_score=profile.quality_score,
    )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_voice_profile(profile_id: str, db: DbSession) -> None:
    profile = db.get(VoiceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="voice profile not found")
    profile.status = "DELETED"
    profile.embedding = None
    profile.embedding_model = None
    profile.embedding_version = None
    for sample in db.scalars(select(VoiceSample).where(VoiceSample.voice_profile_id == profile_id)):
        sample.audio_ref = None
        sample.object_key = None
        sample.retained = False
        sample.deleted_at = datetime.now(timezone.utc)
    db.commit()
