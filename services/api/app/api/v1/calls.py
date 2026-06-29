from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.schemas import CallEvaluateRequest, CallEvaluateResponse
from app.services.risk_service import RiskService


router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/evaluate", response_model=CallEvaluateResponse)
def evaluate_call(request: CallEvaluateRequest, db: DbSession) -> CallEvaluateResponse:
    try:
        evaluation, call_event = RiskService(db).evaluate_phone_number(
            senior_id=request.senior_id,
            phone_number=request.phone_number,
            direction=request.direction,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return CallEvaluateResponse(
        call_event_id=call_event.id,
        risk_score=evaluation.risk_score,
        risk_level=evaluation.risk_level,
        caller_type=evaluation.caller_type,
        action_recommended=evaluation.action_recommended,
        reason_codes=evaluation.reason_codes,
        message_for_senior=evaluation.message_for_senior,
    )

