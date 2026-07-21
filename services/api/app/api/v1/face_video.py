import base64
import binascii
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.config import get_settings
from app.models import FaceProfile, FamilyMember, Senior, VideoVerificationRequest
from app.schemas import (
    FaceProfileCreate,
    FaceProfileResponse,
    FaceProfileUpdate,
    VideoVerificationAccept,
    VideoVerificationCreate,
    VideoVerificationResponse,
)


router = APIRouter(tags=["face-video"])


@router.post(
    "/face-profiles",
    response_model=FaceProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_face_profile(request: FaceProfileCreate, db: DbSession) -> FaceProfile:
    if not db.get(FamilyMember, request.family_member_id):
        raise HTTPException(status_code=404, detail="family member not found")

    if not request.consent_accepted:
        raise HTTPException(status_code=400, detail="face biometric consent required")
    try:
        content_hash, size_bytes, validation_status = _validate_face_image(request.image_ref)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if content_hash and db.scalar(
        select(FaceProfile.id).where(
            FaceProfile.family_member_id == request.family_member_id,
            FaceProfile.content_hash == content_hash,
            FaceProfile.status != "DELETED",
        )
    ):
        raise HTTPException(status_code=409, detail="duplicate face image")
    now = datetime.now(timezone.utc)
    retained_ref = request.image_ref if (
        validation_status == "DEVELOPMENT_REFERENCE" or get_settings().retain_face_images
    ) else None
    profile = FaceProfile(
        family_member_id=request.family_member_id,
        display_name=request.display_name,
        image_ref=retained_ref,
        consent_accepted=True,
        status="ACTIVE",
        content_hash=content_hash,
        size_bytes=size_bytes,
        validation_status=validation_status,
        consented_at=now,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/face-profiles", response_model=list[FaceProfileResponse])
def list_face_profiles(db: DbSession, family_member_id: str | None = None) -> list[FaceProfile]:
    statement = select(FaceProfile).where(FaceProfile.status != "DELETED")
    if family_member_id:
        statement = statement.where(FaceProfile.family_member_id == family_member_id)
    return list(db.scalars(statement))


@router.put("/face-profiles/{profile_id}", response_model=FaceProfileResponse)
def update_face_profile(
    profile_id: str,
    request: FaceProfileUpdate,
    db: DbSession,
) -> FaceProfile:
    profile = db.get(FaceProfile, profile_id)
    if not profile or profile.status == "DELETED":
        raise HTTPException(status_code=404, detail="face profile not found")

    if request.display_name is not None:
        profile.display_name = request.display_name
    if request.image_ref is not None:
        try:
            content_hash, size_bytes, validation_status = _validate_face_image(request.image_ref)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        profile.image_ref = request.image_ref if (
            validation_status == "DEVELOPMENT_REFERENCE" or get_settings().retain_face_images
        ) else None
        profile.content_hash = content_hash
        profile.size_bytes = size_bytes
        profile.validation_status = validation_status
    if request.consent_accepted is not None:
        profile.consent_accepted = request.consent_accepted
        profile.status = "ACTIVE" if request.consent_accepted else "PENDING_CONSENT"
        profile.consented_at = datetime.now(timezone.utc) if request.consent_accepted else None
    if request.match_score is not None:
        profile.match_score = request.match_score
    profile.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/face-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_face_profile(profile_id: str, db: DbSession) -> None:
    profile = db.get(FaceProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="face profile not found")
    profile.status = "DELETED"
    profile.image_ref = None
    profile.consent_accepted = False
    profile.deleted_at = datetime.now(timezone.utc)
    db.commit()


@router.post(
    "/video-verifications",
    response_model=VideoVerificationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_video_verification(
    request: VideoVerificationCreate,
    db: DbSession,
) -> VideoVerificationRequest:
    if not db.get(Senior, request.senior_id):
        raise HTTPException(status_code=404, detail="senior not found")
    if not db.get(FamilyMember, request.family_member_id):
        raise HTTPException(status_code=404, detail="family member not found")

    verification = VideoVerificationRequest(
        senior_id=request.senior_id,
        family_member_id=request.family_member_id,
        risk_event_id=request.risk_event_id,
        status="REQUESTED",
        result="WAITING",
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return verification


@router.get("/video-verifications", response_model=list[VideoVerificationResponse])
def list_video_verifications(
    db: DbSession,
    senior_id: str | None = None,
    family_member_id: str | None = None,
) -> list[VideoVerificationRequest]:
    statement = select(VideoVerificationRequest)
    if senior_id:
        statement = statement.where(VideoVerificationRequest.senior_id == senior_id)
    if family_member_id:
        statement = statement.where(VideoVerificationRequest.family_member_id == family_member_id)
    return list(db.scalars(statement))


@router.post(
    "/video-verifications/{verification_id}/accept",
    response_model=VideoVerificationResponse,
)
def accept_video_verification(
    verification_id: str,
    request: VideoVerificationAccept,
    db: DbSession,
) -> VideoVerificationRequest:
    verification = db.get(VideoVerificationRequest, verification_id)
    if not verification:
        raise HTTPException(status_code=404, detail="video verification not found")

    verification.status = "ACCEPTED"
    verification.match_score = request.match_score
    verification.result = _match_result(request.match_score)
    verification.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(verification)
    return verification


def _match_result(score: int) -> str:
    if score >= 80:
        return "HIGH_MATCH"
    if score >= 55:
        return "NEEDS_REVIEW"
    return "LOW_MATCH"


def _validate_face_image(image_ref: str | None) -> tuple[str | None, int | None, str]:
    if not image_ref:
        raise ValueError("face image is required")
    if not image_ref.startswith("data:"):
        if get_settings().app_env in {"development", "test"}:
            return hashlib.sha256(image_ref.encode()).hexdigest(), len(image_ref.encode()), "DEVELOPMENT_REFERENCE"
        raise ValueError("face image must be an uploaded image")
    try:
        header, encoded = image_ref.split(",", 1)
        mime_type = header.split(";", 1)[0].removeprefix("data:")
        if ";base64" not in header or mime_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise ValueError("unsupported face image type")
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("invalid face image data") from exc
    if not payload:
        raise ValueError("face image is empty")
    if len(payload) > 10 * 1024 * 1024:
        raise ValueError("face image exceeds 10 MB")
    return hashlib.sha256(payload).hexdigest(), len(payload), "VALIDATED"
