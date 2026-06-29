from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import hash_phone_number, phone_last4
from app.models import Family, Guardian, Senior, User
from app.schemas import GuardianCreate, GuardianResponse, SeniorCreate, SeniorResponse


router = APIRouter(prefix="/seniors", tags=["seniors"])


@router.post("", response_model=SeniorResponse, status_code=status.HTTP_201_CREATED)
def create_senior(request: SeniorCreate, db: DbSession) -> Senior:
    if not db.get(Family, request.family_id):
        raise HTTPException(status_code=404, detail="family not found")

    senior = Senior(
        family_id=request.family_id,
        user_id=request.user_id,
        name=request.name,
        phone_number_hash=hash_phone_number(request.phone_number) if request.phone_number else None,
        phone_number_last4=phone_last4(request.phone_number) if request.phone_number else None,
        birth_year=request.birth_year,
    )
    db.add(senior)
    db.commit()
    db.refresh(senior)
    return senior


@router.get("/{senior_id}", response_model=SeniorResponse)
def get_senior(senior_id: str, db: DbSession) -> Senior:
    senior = db.get(Senior, senior_id)
    if not senior:
        raise HTTPException(status_code=404, detail="senior not found")
    return senior


@router.post(
    "/{senior_id}/guardians",
    response_model=GuardianResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_guardian(senior_id: str, request: GuardianCreate, db: DbSession) -> Guardian:
    if not db.get(Senior, senior_id):
        raise HTTPException(status_code=404, detail="senior not found")
    if not db.get(User, request.user_id):
        raise HTTPException(status_code=404, detail="guardian user not found")

    guardian = Guardian(
        senior_id=senior_id,
        user_id=request.user_id,
        relation=request.relation,
        priority=request.priority,
        notify_enabled=request.notify_enabled,
    )
    db.add(guardian)
    db.commit()
    db.refresh(guardian)
    return guardian


@router.get("/{senior_id}/guardians", response_model=list[GuardianResponse])
def list_guardians(senior_id: str, db: DbSession) -> list[Guardian]:
    return list(db.scalars(select(Guardian).where(Guardian.senior_id == senior_id)))

