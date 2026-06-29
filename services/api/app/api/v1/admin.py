from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import hash_phone_number, phone_last4
from app.models import RiskNumber
from app.schemas import RiskNumberCreate, RiskNumberResponse


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/risk-numbers",
    response_model=RiskNumberResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_risk_number(request: RiskNumberCreate, db: DbSession) -> RiskNumber:
    risk_number = RiskNumber(
        phone_number_hash=hash_phone_number(request.phone_number),
        phone_number_last4=phone_last4(request.phone_number),
        label=request.label,
        source=request.source,
        risk_score=request.risk_score,
        active=True,
    )
    db.add(risk_number)
    db.commit()
    db.refresh(risk_number)
    return risk_number


@router.get("/risk-numbers", response_model=list[RiskNumberResponse])
def list_risk_numbers(db: DbSession) -> list[RiskNumber]:
    return list(db.scalars(select(RiskNumber).where(RiskNumber.active.is_(True))))

