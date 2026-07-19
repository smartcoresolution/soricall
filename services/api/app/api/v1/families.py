from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.security import hash_phone_number, hash_verification_code, normalize_phone_number, phone_last4
from app.models import AuditLog, EnrollmentInvitation, FaceProfile, Family, FamilyMember, Guardian, PhoneVerification, SafeWord, Senior
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
    DeviceVerificationConfirmRequest,
    DeviceVerificationRequest,
    PhoneVerificationSendResponse,
    DirectLivenessResponse,
    DirectLivenessVerify,
    DirectLivenessVerifyResponse,
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


@router.delete(
    "/{family_id}/protected-call-users/{protected_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_protected_call_user(family_id: str, protected_user_id: str, db: DbSession) -> None:
    protected_user = db.get(Senior, protected_user_id)
    if not protected_user or protected_user.family_id != family_id:
        raise HTTPException(status_code=404, detail="protected call user not found")
    db.delete(protected_user)
    db.commit()


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
        protected_user_id=protected_user_id,
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
                FamilyMember.protected_user_id == protected_user_id,
                FamilyMember.member_type == "FAMILY_CONFIRMATION_CONTACT",
            )
            .order_by(FamilyMember.notification_priority, FamilyMember.created_at)
        )
    )


@router.delete(
    "/{family_id}/protected-call-users/{protected_user_id}/confirmation-contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_confirmation_contact(
    family_id: str,
    protected_user_id: str,
    contact_id: str,
    db: DbSession,
) -> None:
    protected_user = db.get(Senior, protected_user_id)
    if not protected_user or protected_user.family_id != family_id:
        raise HTTPException(status_code=404, detail="protected call user not found")
    contact = db.get(FamilyMember, contact_id)
    if (
        not contact
        or contact.family_id != family_id
        or contact.protected_user_id != protected_user_id
        or contact.member_type != "FAMILY_CONFIRMATION_CONTACT"
    ):
        raise HTTPException(status_code=404, detail="confirmation contact not found")
    db.delete(contact)
    db.commit()


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
        requested_assets=[asset for asset in invitation.requested_assets.split(",") if asset],
        status=invitation_status,
        sent_at=invitation.sent_at.isoformat(),
        expires_at=invitation.expires_at.isoformat(),
        enrollment_url=enrollment_url,
        member_approval_status=member.approval_status,
        member_trust_level=member.trust_level,
        phone_verified=invitation.phone_verified_at is not None,
    )


@router.post("/{family_id}/members/{member_id}/enrollment-invitations", response_model=EnrollmentInvitationResponse, status_code=201)
def create_enrollment_invitation(
    family_id: str,
    member_id: str,
    db: DbSession,
    channel: str = "LINK",
) -> EnrollmentInvitationResponse:
    member = db.get(FamilyMember, member_id)
    if not member or member.family_id != family_id:
        raise HTTPException(status_code=404, detail="family member not found")
    token = secrets.token_urlsafe(32)
    if channel not in {"LINK", "QR", "DIRECT"}:
        raise HTTPException(status_code=400, detail="unsupported enrollment channel")
    delivery = get_enrollment_delivery_provider().prepare(token)
    now = datetime.now(timezone.utc)
    invitation = EnrollmentInvitation(
        family_id=family_id,
        family_member_id=member_id,
        channel=delivery.channel if channel == "LINK" else channel,
        status="PENDING",
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        sent_at=now,
        expires_at=now + (timedelta(minutes=5) if channel == "QR" else timedelta(days=3)),
    )
    member.approval_status = "INVITED"
    member.is_verified = False
    db.add(invitation)
    db.flush()
    enrollment_url = (
        f"/soricall/enroll?qr_invitation_id={invitation.id}&qr_nonce={token}"
        if channel == "QR"
        else delivery.enrollment_url
    )
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, member, enrollment_url)


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
    invitation.phone_verified_at = None
    invitation.used_at = None
    member.approval_status = "INVITED"
    member.is_verified = False
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, member, delivery.enrollment_url)


def _invitation_for_token(
    token: str,
    db: DbSession,
    *,
    qr_invitation_id: str | None = None,
) -> tuple[EnrollmentInvitation, FamilyMember]:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    invitation = db.scalar(select(EnrollmentInvitation).where(EnrollmentInvitation.token_hash == token_hash))
    if not invitation:
        raise HTTPException(status_code=404, detail="invitation not found")
    if qr_invitation_id is not None and (
        invitation.id != qr_invitation_id or invitation.channel != "QR"
    ):
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
def resolve_enrollment_invitation(
    token: str,
    db: DbSession,
    qr_invitation_id: str | None = None,
) -> EnrollmentInvitationResponse:
    invitation, member = _invitation_for_token(token, db, qr_invitation_id=qr_invitation_id)
    return _invitation_response(invitation, member)


@enrollment_router.post("/direct/liveness", response_model=DirectLivenessResponse)
def create_direct_liveness(token: str, db: DbSession) -> DirectLivenessResponse:
    invitation, _ = _invitation_for_token(token, db)
    if invitation.channel != "DIRECT":
        raise HTTPException(status_code=400, detail="direct enrollment required")
    now = datetime.now(timezone.utc)
    invitation.liveness_action = secrets.choice(["BLINK_TWICE", "TURN_LEFT", "TURN_RIGHT"])
    invitation.liveness_expires_at = now + timedelta(minutes=2)
    invitation.liveness_verified_at = None
    db.commit()
    return DirectLivenessResponse(
        invitation_id=invitation.id,
        action=invitation.liveness_action,
        expires_at=invitation.liveness_expires_at,
    )


@enrollment_router.post("/direct/liveness/verify", response_model=DirectLivenessVerifyResponse)
def verify_direct_liveness(
    token: str, request: DirectLivenessVerify, db: DbSession
) -> DirectLivenessVerifyResponse:
    invitation, _ = _invitation_for_token(token, db)
    now = datetime.now(timezone.utc)
    expires_at = invitation.liveness_expires_at
    if not expires_at or expires_at.replace(tzinfo=expires_at.tzinfo or timezone.utc) <= now:
        raise HTTPException(status_code=410, detail="liveness challenge expired")
    if invitation.liveness_action not in request.observed_actions:
        raise HTTPException(status_code=400, detail="liveness action not observed")
    invitation.liveness_verified_at = now
    invitation.liveness_action = None
    invitation.liveness_expires_at = None
    db.commit()
    return DirectLivenessVerifyResponse(
        invitation_id=invitation.id, verified=True, verified_at=now
    )


@enrollment_router.post(
    "/phone-verification",
    response_model=PhoneVerificationSendResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_enrollment_phone_verification(
    token: str,
    request: DeviceVerificationRequest,
    db: DbSession,
    qr_invitation_id: str | None = None,
) -> PhoneVerificationSendResponse:
    invitation, member = _invitation_for_token(token, db, qr_invitation_id=qr_invitation_id)
    if invitation.status == "EXPIRED":
        raise HTTPException(status_code=410, detail="invitation expired")
    if invitation.channel == "QR" and not invitation.device_verified_at:
        raise HTTPException(status_code=403, detail="QR device verification required")
    if hash_phone_number(request.phone_number) != member.phone_number_hash:
        raise HTTPException(status_code=400, detail="phone number does not match invited family member")
    code = f"{secrets.randbelow(1_000_000):06d}"
    verification = PhoneVerification(
        phone_number=normalize_phone_number(request.phone_number),
        code_hash="pending",
        purpose=f"ENROLLMENT_INVITE:{invitation.id}",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(verification)
    db.flush()
    verification.code_hash = hash_verification_code(verification.id, code)
    db.commit()
    return PhoneVerificationSendResponse(
        verification_id=verification.id,
        expires_in=300,
        development_code=code if get_settings().app_env != "production" else None,
    )


@enrollment_router.post("/phone-verification/confirm", response_model=EnrollmentInvitationResponse)
def confirm_enrollment_phone_verification(
    token: str,
    request: DeviceVerificationConfirmRequest,
    db: DbSession,
    qr_invitation_id: str | None = None,
) -> EnrollmentInvitationResponse:
    invitation, member = _invitation_for_token(token, db, qr_invitation_id=qr_invitation_id)
    verification = db.get(PhoneVerification, request.verification_id)
    now = datetime.now(timezone.utc)
    if not verification or verification.purpose != f"ENROLLMENT_INVITE:{invitation.id}":
        raise HTTPException(status_code=404, detail="phone verification not found")
    expires_at = verification.expires_at if verification.expires_at.tzinfo else verification.expires_at.replace(tzinfo=timezone.utc)
    if verification.consumed_at or expires_at <= now:
        raise HTTPException(status_code=400, detail="phone verification expired")
    verification.attempts += 1
    if verification.attempts > 5:
        db.commit()
        raise HTTPException(status_code=429, detail="phone verification attempts exceeded")
    if not secrets.compare_digest(
        verification.code_hash,
        hash_verification_code(verification.id, request.code),
    ):
        db.commit()
        raise HTTPException(status_code=400, detail="invalid phone verification code")
    verification.consumed_at = now
    invitation.phone_verified_at = now
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, member)


@enrollment_router.post("/complete", response_model=EnrollmentInvitationResponse)
def complete_enrollment_invitation(
    token: str,
    request: EnrollmentCompleteRequest,
    db: DbSession,
    qr_invitation_id: str | None = None,
) -> EnrollmentInvitationResponse:
    invitation, member = _invitation_for_token(token, db, qr_invitation_id=qr_invitation_id)
    if invitation.status == "EXPIRED":
        raise HTTPException(status_code=410, detail="invitation expired")
    if invitation.status == "COMPLETED":
        if invitation.channel == "QR":
            db.add(AuditLog(
                actor_user_id=current_user_id.get(),
                action="QR_REPLAY_REJECTED",
                resource_type="ENROLLMENT_INVITATION",
                resource_id=invitation.id,
                metadata_json='{"reason":"consumed QR invitation presented again"}',
            ))
            db.commit()
            raise HTTPException(status_code=409, detail="QR invitation already used")
        return _invitation_response(invitation, member)
    if invitation.channel == "DIRECT" and not invitation.liveness_verified_at:
        raise HTTPException(status_code=409, detail="direct liveness verification required")
    if not invitation.phone_verified_at:
        raise HTTPException(status_code=400, detail="invited family phone verification required")
    if not request.consent_accepted:
        raise HTTPException(status_code=400, detail="consent required")

    voice_service = VoiceProfileService(db)
    try:
        voice_service.validate_sample(
            audio_ref=request.audio_ref,
            duration_ms=request.duration_ms,
            mime_type=request.mime_type,
            purpose="ENROLLMENT",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
        from app.api.v1.face_video import _validate_face_image
        from app.core.config import get_settings

        try:
            content_hash, size_bytes, validation_status = _validate_face_image(request.face_image_ref)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        db.add(FaceProfile(
            family_member_id=member.id,
            display_name=member.name,
            image_ref=request.face_image_ref if (
                validation_status == "DEVELOPMENT_REFERENCE" or get_settings().retain_face_images
            ) else None,
            consent_accepted=True,
            status="ACTIVE",
            content_hash=content_hash,
            size_bytes=size_bytes,
            validation_status=validation_status,
            consented_at=datetime.now(timezone.utc),
        ))
    invitation.status = "COMPLETED"
    invitation.used_at = datetime.now(timezone.utc)
    invitation.completed_at = datetime.now(timezone.utc)
    invitation.liveness_action = None
    invitation.liveness_expires_at = None
    member.approval_status = "REVIEW_REQUIRED"
    member.trust_level = "B"
    member.is_verified = False
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, member)


def _confirmation_contact_for_transition(
    family_id: str,
    protected_user_id: str,
    contact_id: str,
    db: DbSession,
) -> FamilyMember:
    protected_user = db.get(Senior, protected_user_id)
    if not protected_user or protected_user.family_id != family_id:
        raise HTTPException(status_code=404, detail="protected call user not found")
    actor_id = current_user_id.get()
    if actor_id and protected_user.user_id != actor_id:
        raise HTTPException(status_code=403, detail="protected user approval required")
    contact = db.get(FamilyMember, contact_id)
    if (
        not contact
        or contact.family_id != family_id
        or contact.protected_user_id != protected_user_id
        or contact.member_type != "FAMILY_CONFIRMATION_CONTACT"
    ):
        raise HTTPException(status_code=404, detail="confirmation contact not found")
    return contact


def _audit_member_transition(db: DbSession, member: FamilyMember, action: str) -> None:
    db.add(
        AuditLog(
            actor_user_id=current_user_id.get(),
            action=action,
            resource_type="FAMILY_MEMBER",
            resource_id=member.id,
            metadata_json=f'{{"approval_status":"{member.approval_status}","trust_level":"{member.trust_level}"}}',
        )
    )


@router.post(
    "/{family_id}/protected-call-users/{protected_user_id}/confirmation-contacts/{contact_id}/approve",
    response_model=ConfirmationContactResponse,
)
def approve_confirmation_contact(
    family_id: str,
    protected_user_id: str,
    contact_id: str,
    db: DbSession,
) -> FamilyMember:
    contact = _confirmation_contact_for_transition(family_id, protected_user_id, contact_id, db)
    if contact.approval_status != "REVIEW_REQUIRED":
        raise HTTPException(status_code=409, detail="confirmation contact is not ready for approval")
    now = datetime.now(timezone.utc)
    contact.approval_status = "ACTIVE"
    contact.is_verified = True
    contact.approved_at = now
    contact.approved_by = current_user_id.get()
    contact.revoked_at = None
    contact.revocation_reason = None
    _audit_member_transition(db, contact, "FAMILY_MEMBER_APPROVED")
    db.commit()
    db.refresh(contact)
    return contact


@router.post(
    "/{family_id}/protected-call-users/{protected_user_id}/confirmation-contacts/{contact_id}/reverify",
    response_model=ConfirmationContactResponse,
)
def reverify_confirmation_contact(
    family_id: str,
    protected_user_id: str,
    contact_id: str,
    db: DbSession,
) -> FamilyMember:
    contact = _confirmation_contact_for_transition(family_id, protected_user_id, contact_id, db)
    if contact.approval_status != "ACTIVE":
        raise HTTPException(status_code=409, detail="only active confirmation contacts can be reverified")
    contact.approval_status = "REVERIFY"
    contact.is_verified = False
    _audit_member_transition(db, contact, "FAMILY_MEMBER_REVERIFY_REQUESTED")
    db.commit()
    db.refresh(contact)
    return contact


@router.post(
    "/{family_id}/protected-call-users/{protected_user_id}/confirmation-contacts/{contact_id}/revoke",
    response_model=ConfirmationContactResponse,
)
def revoke_confirmation_contact(
    family_id: str,
    protected_user_id: str,
    contact_id: str,
    db: DbSession,
    reason: str | None = None,
) -> FamilyMember:
    contact = _confirmation_contact_for_transition(family_id, protected_user_id, contact_id, db)
    if contact.approval_status == "REVOKED":
        return contact
    contact.approval_status = "REVOKED"
    contact.is_verified = False
    contact.revoked_at = datetime.now(timezone.utc)
    contact.revocation_reason = reason
    _audit_member_transition(db, contact, "FAMILY_MEMBER_REVOKED")
    db.commit()
    db.refresh(contact)
    return contact


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
