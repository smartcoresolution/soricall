from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import hash_phone_number, phone_last4
from app.models import Family, FamilyMember, SafeWord, Senior
from app.schemas import (
    FamilyCreate,
    FamilyMemberCreate,
    FamilyMemberResponse,
    FamilyResponse,
    ProtectedCallUserCreate,
    ProtectedCallUserResponse,
    ConfirmationContactCreate,
    ConfirmationContactResponse,
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
