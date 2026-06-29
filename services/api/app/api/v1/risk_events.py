from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import RiskEvent, Senior
from app.schemas import RiskEventCreate, RiskEventResponse


router = APIRouter(prefix="/risk-events", tags=["risk-events"])


@router.post("", response_model=RiskEventResponse, status_code=status.HTTP_201_CREATED)
def create_risk_event(request: RiskEventCreate, db: DbSession) -> RiskEventResponse:
    if not db.get(Senior, request.senior_id):
        raise HTTPException(status_code=404, detail="senior not found")

    risk_event = RiskEvent(
        senior_id=request.senior_id,
        call_event_id=request.call_event_id,
        event_type=request.event_type,
        risk_score=request.risk_score,
        risk_level=request.risk_level,
        reason_codes=",".join(request.reason_codes),
        summary=request.summary,
    )
    db.add(risk_event)
    db.commit()
    db.refresh(risk_event)
    return _risk_event_response(risk_event)


@router.get("", response_model=list[RiskEventResponse])
def list_risk_events(db: DbSession, senior_id: str | None = None) -> list[RiskEventResponse]:
    statement = select(RiskEvent)
    if senior_id:
        statement = statement.where(RiskEvent.senior_id == senior_id)
    return [_risk_event_response(event) for event in db.scalars(statement)]


@router.get("/{event_id}", response_model=RiskEventResponse)
def get_risk_event(event_id: str, db: DbSession) -> RiskEventResponse:
    risk_event = db.get(RiskEvent, event_id)
    if not risk_event:
        raise HTTPException(status_code=404, detail="risk event not found")
    return _risk_event_response(risk_event)


def _risk_event_response(risk_event: RiskEvent) -> RiskEventResponse:
    return RiskEventResponse(
        id=risk_event.id,
        senior_id=risk_event.senior_id,
        call_event_id=risk_event.call_event_id,
        event_type=risk_event.event_type,
        risk_score=risk_event.risk_score,
        risk_level=risk_event.risk_level,
        reason_codes=[code for code in risk_event.reason_codes.split(",") if code],
        summary=risk_event.summary,
    )

