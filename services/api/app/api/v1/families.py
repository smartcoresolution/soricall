from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.api.deps import DbSession
from app.core.security import hash_phone_number, phone_last4
from app.models import EnrollmentInvitation, FaceProfile, Family, FamilyMember, Guardian, SafeWord, Senior
from app.schemas import (
    FamilyCreate,
    FamilyMemberCreate,
    FamilyMemberResponse,
    FamilyResponse,
    ProtectedCallUserCreate,
    ProtectedCallUserResponse,
    ConfirmationContactCreate,
    ConfirmationContactResponse,
    EnrollmentInvitationResponse,
    EnrollmentCompleteRequest,
    SafeWordResponse,
    SafeWordUpsert,
    SafeWordVerifyRequest,
    SafeWordVerifyResponse,
)
from app.core.security import hash_safe_word
from app.core.authorization import current_user_id
from app.services.voice_profile_service import VoiceProfileService
from app.services.enrollment_delivery_service import get_enrollment_delivery_provider


router = APIRouter(prefix="/families", tags=["families"])
enrollment_router = APIRouter(prefix="/enrollment-invitations", tags=["enrollment-invitations"])


@router.post("", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
def create_family(request: FamilyCreate, db: DbSession) -> Family:
    # HTTP requests always use the authenticated identity. The fallback keeps direct
    # service-level tests and internal calls backwards compatible.
    family = Family(name=request.name, created_by=current_user_id.get() or request.created_by)
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


@router.get("", response_model=list[FamilyResponse])
def list_accessible_families(db: DbSession) -> list[Family]:
    user_id = current_user_id.get()
    if not user_id:
        return []
    member_family_ids = select(FamilyMember.family_id).where(FamilyMember.user_id == user_id)
    senior_family_ids = select(Senior.family_id).where(Senior.user_id == user_id)
    guardian_family_ids = (
        select(Senior.family_id)
        .join(Guardian, Guardian.senior_id == Senior.id)
        .where(Guardian.user_id == user_id)
    )
    return list(db.scalars(
        select(Family)
        .where(or_(
            Family.created_by == user_id,
            Family.id.in_(member_family_ids),
            Family.id.in_(senior_family_ids),
            Family.id.in_(guardian_family_ids),
        ))
        .order_by(Family.created_at)
    ))


@router.get("/{family_id}", response_model=FamilyResponse)
def get_family(family_id: str, db: DbSession) -> Family:
    family = db.get(Family, family_id)
    if not family:
        raise HTTPException(status_code=404, detail="family not found")
    return family


@router.post(
    "/{family_id}/members",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_family_member(family_id: str, request: FamilyMemberCreate, db: DbSession) -> FamilyMember:
    if not db.get(Family, family_id):
        raise HTTPException(status_code=404, detail="family not found")

    member = FamilyMember(
        family_id=family_id,
        user_id=request.user_id,
        name=request.name,
        relation=request.relation,
        phone_number_hash=hash_phone_number(request.phone_number) if request.phone_number else None,
        phone_number_last4=phone_last4(request.phone_number) if request.phone_number else None,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/{family_id}/members", response_model=list[FamilyMemberResponse])
def list_family_members(family_id: str, db: DbSession) -> list[FamilyMember]:
    return list(db.scalars(select(FamilyMember).where(FamilyMember.family_id == family_id)))


@router.post(
    "/{family_id}/protected-call-users",
    response_model=ProtectedCallUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_protected_call_user(
    family_id: str,
    request: ProtectedCallUserCreate,
    db: DbSession,
) -> Senior:
    if not db.get(Family, family_id):
        raise HTTPException(status_code=404, detail="family not found")
    protected_user = Senior(
        family_id=family_id,
        user_id=request.user_id,
        name=request.name,
        member_type="PROTECTED_CALL_USER",
        relation_code=request.relation_code,
        protection_status="PREPARING",
        phone_number_hash=hash_phone_number(request.phone_number),
        phone_number_last4=phone_last4(request.phone_number),
    )
    db.add(protected_user)
    db.commit()
    db.refresh(protected_user)
    return protected_user


@router.get(
    "/{family_id}/protected-call-users",
    response_model=list[ProtectedCallUserResponse],
)
def list_protected_call_users(family_id: str, db: DbSession) -> list[Senior]:
    return list(db.scalars(select(Senior).where(Senior.family_id == family_id)))


@router.post(
    "/{family_id}/protected-call-users/{protected_user_id}/confirmation-contacts",
    response_model=ConfirmationContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_confirmation_contact(
    family_id: str,
    protected_user_id: str,
    request: ConfirmationContactCreate,
    db: DbSession,
) -> FamilyMember:
    protected_user = db.get(Senior, protected_user_id)
    if not protected_user or protected_user.family_id != family_id:
        raise HTTPException(status_code=404, detail="protected call user not found")
    contact = FamilyMember(
        family_id=family_id,
        user_id=request.user_id,
        name=request.name,
        relation=request.relation_code,
        member_type="FAMILY_CONFIRMATION_CONTACT",
        relation_code=request.relation_code,
        phone_number_hash=hash_phone_number(request.phone_number),
        phone_number_last4=phone_last4(request.phone_number),
        is_primary_contact=request.is_primary_contact,
        notification_priority=request.notification_priority,
        notify_enabled=request.notify_enabled,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get(
    "/{family_id}/protected-call-users/{protected_user_id}/confirmation-contacts",
    response_model=list[ConfirmationContactResponse],
)
def list_confirmation_contacts(
    family_id: str,
    protected_user_id: str,
    db: DbSession,
) -> list[FamilyMember]:
    protected_user = db.get(Senior, protected_user_id)
    if not protected_user or protected_user.family_id != family_id:
        raise HTTPException(status_code=404, detail="protected call user not found")
    return list(
        db.scalars(
            select(FamilyMember)
            .where(
                FamilyMember.family_id == family_id,
                FamilyMember.member_type == "FAMILY_CONFIRMATION_CONTACT",
            )
            .order_by(FamilyMember.notification_priority, FamilyMember.created_at)
        )
    )


def _invitation_response(invitation: EnrollmentInvitation, member: FamilyMember, enrollment_url: str | None = None) -> EnrollmentInvitationResponse:
    now = datetime.now(timezone.utc)
    expires_at = invitation.expires_at if invitation.expires_at.tzinfo else invitation.expires_at.replace(tzinfo=timezone.utc)
    invitation_status = "EXPIRED" if invitation.status == "PENDING" and expires_at <= now else invitation.status
    return EnrollmentInvitationResponse(
        id=invitation.id,
        family_id=invitation.family_id,
        family_member_id=invitation.family_member_id,
        family_member_name=member.name,
        relation_code=member.relation_code,
        phone_number_last4=member.phone_number_last4,
        channel=invitation.channel,
        status=invitation_status,
        sent_at=invitation.sent_at.isoformat(),
        expires_at=invitation.expires_at.isoformat(),
        enrollment_url=enrollment_url,
    )


@router.post("/{family_id}/members/{member_id}/enrollment-invitations", response_model=EnrollmentInvitationResponse, status_code=201)
def create_enrollment_invitation(family_id: str, member_id: str, db: DbSession) -> EnrollmentInvitationResponse:
    member = db.get(FamilyMember, member_id)
    if not member or member.family_id != family_id:
        raise HTTPException(status_code=404, detail="family member not found")
    token = secrets.token_urlsafe(32)
    delivery = get_enrollment_delivery_provider().prepare(token)
    now = datetime.now(timezone.utc)
    invitation = EnrollmentInvitation(
        family_id=family_id,
        family_member_id=member_id,
        channel=delivery.channel,
        status="PENDING",
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        sent_at=now,
        expires_at=now + timedelta(days=3),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, member, delivery.enrollment_url)


@router.get("/{family_id}/enrollment-invitations", response_model=list[EnrollmentInvitationResponse])
def list_enrollment_invitations(family_id: str, db: DbSession) -> list[EnrollmentInvitationResponse]:
    invitations = list(db.scalars(select(EnrollmentInvitation).where(EnrollmentInvitation.family_id == family_id).order_by(EnrollmentInvitation.created_at)))
    members = {member.id: member for member in db.scalars(select(FamilyMember).where(FamilyMember.family_id == family_id))}
    return [_invitation_response(invitation, members[invitation.family_member_id]) for invitation in invitations if invitation.family_member_id in members]


@router.post("/{family_id}/enrollment-invitations/{invitation_id}/resend", response_model=EnrollmentInvitationResponse)
def resend_enrollment_invitation(family_id: str, invitation_id: str, db: DbSession) -> EnrollmentInvitationResponse:
    invitation = db.get(EnrollmentInvitation, invitation_id)
    if not invitation or invitation.family_id != family_id:
        raise HTTPException(status_code=404, detail="invitation not found")
    member = db.get(FamilyMember, invitation.family_member_id)
    if not member:
        raise HTTPException(status_code=404, detail="family member not found")
    token = secrets.token_urlsafe(32)
    delivery = get_enrollment_delivery_provider().prepare(token)
    now = datetime.now(timezone.utc)
    invitation.token_hash = hashlib.sha256(token.encode()).hexdigest()
    invitation.channel = delivery.channel
    invitation.status = "PENDING"
    invitation.sent_at = now
    invitation.expires_at = now + timedelta(days=3)
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, member, delivery.enrollment_url)


def _invitation_for_token(token: str, db: DbSession) -> tuple[EnrollmentInvitation, FamilyMember]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    invitation = db.scalar(select(EnrollmentInvitation).where(EnrollmentInvitation.token_hash == token_hash))
    if not invitation:
        raise HTTPException(status_code=404, detail="invitation not found")
    member = db.get(FamilyMember, invitation.family_member_id)
    if not member:
        raise HTTPException(status_code=404, detail="family member not found")
    expires_at = invitation.expires_at if invitation.expires_at.tzinfo else invitation.expires_at.replace(tzinfo=timezone.utc)
    if invitation.status == "PENDING" and expires_at <= datetime.now(timezone.utc):
        invitation.status = "EXPIRED"
        db.commit()
    return invitation, member


@enrollment_router.get("/resolve", response_model=EnrollmentInvitationResponse)
def resolve_enrollment_invitation(token: str, db: DbSession) -> EnrollmentInvitationResponse:
    invitation, member = _invitation_for_token(token, db)
    return _invitation_response(invitation, member)


@enrollment_router.post("/complete", response_model=EnrollmentInvitationResponse)
def complete_enrollment_invitation(
    token: str,
    request: EnrollmentCompleteRequest,
    db: DbSession,
) -> EnrollmentInvitationResponse:
    invitation, member = _invitation_for_token(token, db)
    if invitation.status == "EXPIRED":
        raise HTTPException(status_code=410, detail="invitation expired")
    if invitation.status == "COMPLETED":
        return _invitation_response(invitation, member)
    if not request.consent_accepted:
        raise HTTPException(status_code=400, detail="consent required")

    voice_service = VoiceProfileService(db)
    profile = voice_service.create_profile(
        family_member_id=member.id,
        display_name=member.name,
        consent_id=invitation.id,
    )
    voice_service.add_sample(
        voice_profile_id=profile.id,
        audio_ref=request.audio_ref,
        object_key=None,
        duration_ms=request.duration_ms,
        sample_rate=None,
        mime_type=request.mime_type,
        purpose="ENROLLMENT",
    )
    voice_service.enroll(voice_profile_id=profile.id, audio_ref=request.audio_ref)
    if request.face_image_ref:
        db.add(FaceProfile(
            family_member_id=member.id,
            display_name=member.name,
            image_ref=request.face_image_ref,
            consent_accepted=True,
            status="ACTIVE",
        ))
    invitation.status = "COMPLETED"
    invitation.completed_at = datetime.now(timezone.utc)
    member.is_verified = True
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, member)


@router.post("/{family_id}/safe-word", response_model=SafeWordResponse, status_code=201)
def upsert_safe_word(family_id: str, request: SafeWordUpsert, db: DbSession) -> SafeWord:
    if not db.get(Family, family_id):
        raise HTTPException(status_code=404, detail="family not found")

    safe_word = db.scalar(select(SafeWord).where(SafeWord.family_id == family_id))
    if safe_word:
        safe_word.word_hash = hash_safe_word(request.word)
        safe_word.hint = request.hint
        safe_word.updated_by = request.updated_by
    else:
        safe_word = SafeWord(
            family_id=family_id,
            word_hash=hash_safe_word(request.word),
            hint=request.hint,
            updated_by=request.updated_by,
        )
        db.add(safe_word)

    db.commit()
    db.refresh(safe_word)
    return safe_word


@router.put("/{family_id}/safe-word", response_model=SafeWordResponse)
def update_safe_word(family_id: str, request: SafeWordUpsert, db: DbSession) -> SafeWord:
    return upsert_safe_word(family_id, request, db)


@router.post("/{family_id}/safe-word/verify", response_model=SafeWordVerifyResponse)
def verify_safe_word(
    family_id: str,
    request: SafeWordVerifyRequest,
    db: DbSession,
) -> SafeWordVerifyResponse:
    safe_word = db.scalar(select(SafeWord).where(SafeWord.family_id == family_id))
    if not safe_word:
        raise HTTPException(status_code=404, detail="safe word not found")

    return SafeWordVerifyResponse(matched=safe_word.word_hash == hash_safe_word(request.word))
