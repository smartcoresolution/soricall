from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import hash_phone_number, phone_last4
from app.models import Family, FamilyMember, SafeWord
from app.schemas import (
    FamilyCreate,
    FamilyMemberCreate,
    FamilyMemberResponse,
    FamilyResponse,
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

