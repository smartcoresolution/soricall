from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.schemas import (
    CallAnalysisSubmit,
    CallAnalysisSubmitResponse,
    CallSessionCreate,
    CallSessionCreateResponse,
    CallVoiceAnalysisRequest,
    CallVoiceAnalysisResponse,
    FamilyConfirmationCreate,
    FamilyConfirmationCreateResponse,
    FamilyConfirmationRespond,
    FamilyConfirmationRespondResponse,
    PushTokenRegister,
    PushTokenResponse,
    ResponseActionResult,
    ResponseActionResultResponse,
)
from app.models import DevicePushToken, Guardian, ResponseAction
from app.core.authorization import current_user_id
from sqlalchemy import select
from datetime import datetime, timezone
from app.services.call_analysis_service import CallAnalysisService
from app.services.call_session_service import CallSessionService
from app.services.family_confirmation_service import FamilyConfirmationService
from app.services.voice_call_analysis_service import VoiceCallAnalysisService


router = APIRouter(prefix="/call-sessions", tags=["call-sessions"])
confirmation_router = APIRouter(prefix="/family-confirmations", tags=["family-confirmations"])
push_router = APIRouter(prefix="/guardians", tags=["push-notifications"])
device_push_router = APIRouter(prefix="/device-push-tokens", tags=["push-notifications"])


@router.post("", response_model=CallSessionCreateResponse, status_code=status.HTTP_201_CREATED)
def create_call_session(
    request: CallSessionCreate,
    db: DbSession,
) -> CallSessionCreateResponse:
    try:
        result = CallSessionService(db).create(
            senior_id=request.senior_id,
            phone_number=request.phone_number,
            direction=request.direction,
        )
    except ValueError as exc:
        status_code = 404 if str(exc) == "senior not found" else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return CallSessionCreateResponse(
        call_session_id=result.call_session.id,
        family_number_matched=result.call_session.family_number_matched,
        matched_family_member_id=result.call_session.matched_family_member_id,
        suspected=result.call_session.suspected,
        status=result.call_session.status,
        risk_decision_id=result.risk_decision.id,
        risk_score=result.risk_decision.risk_score,
        risk_level=result.risk_decision.risk_level,
        decision=result.risk_decision.decision,
        reason_codes=result.reason_codes,
        response_action_id=result.response_action.id,
    )


@router.post(
    "/{call_session_id}/analyses",
    response_model=CallAnalysisSubmitResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_call_analysis(
    call_session_id: str,
    request: CallAnalysisSubmit,
    db: DbSession,
) -> CallAnalysisSubmitResponse:
    try:
        result = CallAnalysisService(db).submit(
            call_session_id=call_session_id,
            speaker_similarity=request.speaker_similarity,
            spoof_probability=request.spoof_probability,
            content_risk_score=request.content_risk_score,
            content_reason_codes=request.content_reason_codes,
            face_match_score=request.face_match_score,
            model_versions=request.model_versions,
        )
    except ValueError as exc:
        status_code = 404 if str(exc) == "call session not found" else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    decision = result.risk_decision
    return CallAnalysisSubmitResponse(
        call_session_id=decision.call_session_id,
        risk_decision_id=decision.id,
        sequence=decision.sequence,
        risk_score=decision.risk_score,
        risk_level=decision.risk_level,
        decision=decision.decision,
        reason_codes=result.reason_codes,
        response_action_id=result.response_action.id,
    )


@router.post(
    "/{call_session_id}/voice-analysis",
    response_model=CallVoiceAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def analyze_call_voice(
    call_session_id: str,
    request: CallVoiceAnalysisRequest,
    db: DbSession,
) -> CallVoiceAnalysisResponse:
    try:
        result = VoiceCallAnalysisService(db).analyze(
            call_session_id=call_session_id,
            voice_profile_id=request.voice_profile_id,
            audio_ref=request.audio_ref,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    decision = result.risk_decision
    return CallVoiceAnalysisResponse(
        call_session_id=decision.call_session_id,
        risk_decision_id=decision.id,
        sequence=decision.sequence,
        risk_score=decision.risk_score,
        risk_level=decision.risk_level,
        decision=decision.decision,
        reason_codes=result.reason_codes,
        response_action_id=result.response_action.id,
        transcript=decision.transcript or "",
        transcript_language=decision.transcript_language or "",
        transcript_confidence=decision.transcript_confidence or 0,
        speaker_similarity=decision.speaker_similarity or 0,
        spoof_probability=decision.spoof_probability or 0,
    )


@router.post(
    "/{call_session_id}/family-confirmations",
    response_model=FamilyConfirmationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_family_confirmation(
    call_session_id: str,
    request: FamilyConfirmationCreate,
    db: DbSession,
) -> FamilyConfirmationCreateResponse:
    try:
        confirmation = FamilyConfirmationService(db).request(
            call_session_id=call_session_id,
            family_member_id=request.family_member_id,
            guardian_id=request.guardian_id,
            channel=request.channel,
            expires_in_seconds=request.expires_in_seconds,
        )
    except ValueError as exc:
        status_code = 404 if str(exc) in {"call session not found", "senior not found"} else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return FamilyConfirmationCreateResponse(
        confirmation_id=confirmation.id,
        call_session_id=confirmation.call_session_id,
        status=confirmation.status,
        channel=confirmation.channel,
        expires_at=confirmation.expires_at.isoformat() if confirmation.expires_at else "",
    )


@confirmation_router.post(
    "/{confirmation_id}/respond",
    response_model=FamilyConfirmationRespondResponse,
)
def respond_to_family_confirmation(
    confirmation_id: str,
    request: FamilyConfirmationRespond,
    db: DbSession,
) -> FamilyConfirmationRespondResponse:
    try:
        result = FamilyConfirmationService(db).respond(
            confirmation_id=confirmation_id,
            response=request.response,
        )
    except ValueError as exc:
        if str(exc) in {"family confirmation not found", "call session not found"}:
            status_code = 404
        elif str(exc) in {"family confirmation already responded", "family confirmation expired"}:
            status_code = 409
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return FamilyConfirmationRespondResponse(
        confirmation_id=result.confirmation.id,
        call_session_id=result.confirmation.call_session_id,
        status=result.confirmation.status,
        response=result.confirmation.response or "UNKNOWN",
        risk_decision_id=result.risk_decision.id,
        risk_score=result.risk_decision.risk_score,
        risk_level=result.risk_decision.risk_level,
        decision=result.risk_decision.decision,
        reason_codes=result.reason_codes,
        response_action_id=result.response_action.id,
    )


@push_router.post("/{guardian_id}/push-tokens", response_model=PushTokenResponse, status_code=201)
def register_push_token(guardian_id: str, request: PushTokenRegister, db: DbSession) -> DevicePushToken:
    if not db.get(Guardian, guardian_id):
        raise HTTPException(status_code=404, detail="guardian not found")
    token = DevicePushToken(guardian_id=guardian_id, token=request.token, platform=request.platform)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


@device_push_router.post("", response_model=PushTokenResponse)
def register_current_user_push_tokens(
    request: PushTokenRegister,
    db: DbSession,
) -> DevicePushToken:
    user_id = current_user_id.get()
    if not user_id:
        raise HTTPException(status_code=401, detail="authentication required")
    guardians = list(db.scalars(select(Guardian).where(Guardian.user_id == user_id)))
    if not guardians:
        raise HTTPException(status_code=409, detail="current user has no guardian assignment")

    existing = db.scalar(select(DevicePushToken).where(DevicePushToken.token == request.token))
    target_guardian_ids = {guardian.id for guardian in guardians}
    if existing:
        if existing.guardian_id not in target_guardian_ids:
            raise HTTPException(status_code=409, detail="push token belongs to another user")
        existing.platform = request.platform
        existing.active = True
        tokens = [existing]
    else:
        tokens = [
            DevicePushToken(guardian_id=guardian.id, token=request.token, platform=request.platform)
            for guardian in guardians
        ]
        # The token column is intentionally unique. A single installation is
        # therefore associated with the user's first guardian assignment.
        tokens = tokens[:1]
        db.add_all(tokens)
    db.commit()
    for token in tokens:
        db.refresh(token)
    return tokens[0]


@router.post(
    "/{call_session_id}/actions/{action_id}/result",
    response_model=ResponseActionResultResponse,
)
def report_response_action(
    call_session_id: str,
    action_id: str,
    request: ResponseActionResult,
    db: DbSession,
) -> ResponseAction:
    action = db.get(ResponseAction, action_id)
    if not action or action.call_session_id != call_session_id:
        raise HTTPException(status_code=404, detail="response action not found")
    action.status = request.status
    action.failure_reason = request.failure_reason
    action.executed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(action)
    return action
