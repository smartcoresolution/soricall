from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
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

    profile = FaceProfile(
        family_member_id=request.family_member_id,
        display_name=request.display_name,
        image_ref=request.image_ref,
        consent_accepted=request.consent_accepted,
        status="ACTIVE" if request.consent_accepted else "PENDING_CONSENT",
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
        profile.image_ref = request.image_ref
    if request.consent_accepted is not None:
        profile.consent_accepted = request.consent_accepted
        profile.status = "ACTIVE" if request.consent_accepted else "PENDING_CONSENT"
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
