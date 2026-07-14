from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import hash_phone_number, phone_last4
from app.models import EnrollmentInvitation, Family, FamilyMember, SafeWord, Senior
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
    SafeWordResponse,
    SafeWordUpsert,
    SafeWordVerifyRequest,
    SafeWordVerifyResponse,
)
from app.core.security import hash_safe_word


router = APIRouter(prefix="/families", tags=["families"])


@router.post("", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
def create_family(request: FamilyCreate, db: DbSession) -> Family:
    family = Family(name=request.name, created_by=request.created_by)
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


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
    now = datetime.now(timezone.utc)
    invitation = EnrollmentInvitation(
        family_id=family_id,
        family_member_id=member_id,
        channel="SMS",
        status="PENDING",
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        sent_at=now,
        expires_at=now + timedelta(days=3),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, member, f"/soricall/enroll?token={token}")


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
    now = datetime.now(timezone.utc)
    invitation.token_hash = hashlib.sha256(token.encode()).hexdigest()
    invitation.status = "PENDING"
    invitation.sent_at = now
    invitation.expires_at = now + timedelta(days=3)
    db.commit()
    db.refresh(invitation)
    return _invitation_response(invitation, member, f"/soricall/enroll?token={token}")


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
