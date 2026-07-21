from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
import json

from sqlalchemy import func, select

from app.api.deps import DbSession
from app.core.security import hash_phone_number, phone_last4
from app.core.authorization import current_user_id
from app.models import (
    AuditLog, CallEvent, CallSession, ConsentLog, DeviceEnrollment, EmergencyNotification,
    FaceProfile, Family, FamilyConfirmation, FamilyMember, PushDelivery, ResponseAction,
    RiskDecision, RiskEvent, RiskNumber, Senior, User, VideoVerificationRequest,
    VoiceProfile, VoiceSample,
)
from app.schemas import RiskNumberCreate, RiskNumberResponse


router = APIRouter(prefix="/admin", tags=["admin"])


def _mask_name(value: str | None) -> str:
    if not value:
        return "-"
    if len(value) == 1:
        return value
    return value[0] + "*" * (len(value) - 1)


def _mask_phone(last4: str | None) -> str:
    return f"010-****-{last4}" if last4 else "-"


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _audit(db: DbSession, action: str, resource_type: str, resource_id: str | None = None, metadata: dict | None = None) -> None:
    db.add(AuditLog(
        actor_user_id=current_user_id.get(), action=action, resource_type=resource_type,
        resource_id=resource_id, metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    ))
    db.commit()


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
    return list(db.scalars(select(RiskNumber).where(RiskNumber.active.is_(True)).order_by(RiskNumber.created_at.desc())))


@router.delete("/risk-numbers/{risk_number_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_risk_number(risk_number_id: str, db: DbSession) -> None:
    risk_number = db.get(RiskNumber, risk_number_id)
    if not risk_number or not risk_number.active:
        raise HTTPException(status_code=404, detail="risk number not found")
    risk_number.active = False
    db.commit()


@router.get("/dashboard")
def get_dashboard(db: DbSession) -> dict:
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = today.replace(day=1)
    risk_levels = dict(db.execute(
        select(CallEvent.risk_level, func.count(CallEvent.id))
        .where(CallEvent.occurred_at >= today)
        .group_by(CallEvent.risk_level)
    ).all())
    recent_events = list(db.scalars(select(RiskEvent).order_by(RiskEvent.created_at.desc()).limit(10)))
    return {
        "generated_at": now.isoformat(),
        "metrics": {
            "users": db.scalar(select(func.count(User.id))) or 0,
            "families": db.scalar(select(func.count(Family.id))) or 0,
            "protected_users": db.scalar(select(func.count(Senior.id))) or 0,
            "monthly_calls": db.scalar(select(func.count(CallEvent.id)).where(CallEvent.occurred_at >= month)) or 0,
            "monthly_risk_events": db.scalar(select(func.count(RiskEvent.id)).where(RiskEvent.created_at >= month)) or 0,
            "active_devices": db.scalar(select(func.count(DeviceEnrollment.id)).where(DeviceEnrollment.status == "ACTIVE")) or 0,
        },
        "today": {
            "total": sum(risk_levels.values()),
            "safe": risk_levels.get("LOW", 0),
            "warning": risk_levels.get("MEDIUM", 0),
            "danger": risk_levels.get("HIGH", 0) + risk_levels.get("CRITICAL", 0),
        },
        "recent_events": [{
            "id": event.id,
            "risk_level": event.risk_level,
            "risk_score": event.risk_score,
            "event_type": event.event_type,
            "summary": event.summary,
            "created_at": event.created_at.isoformat(),
        } for event in recent_events],
    }


@router.get("/overview")
def get_admin_overview(db: DbSession) -> dict:
    seniors = list(db.scalars(select(Senior).order_by(Senior.created_at.desc()).limit(500)))
    members = list(db.scalars(select(FamilyMember).order_by(FamilyMember.created_at.desc()).limit(1000)))
    voice_profiles = list(db.scalars(select(VoiceProfile).where(VoiceProfile.status != "DELETED")))
    face_profiles = list(db.scalars(select(FaceProfile).where(FaceProfile.status != "DELETED")))
    voice_samples = list(db.scalars(select(VoiceSample).where(VoiceSample.deleted_at.is_(None))))
    devices = list(db.scalars(select(DeviceEnrollment)))
    sessions = list(db.scalars(select(CallSession).order_by(CallSession.started_at.desc()).limit(500)))
    decisions = list(db.scalars(select(RiskDecision).order_by(RiskDecision.created_at.desc()).limit(1000)))
    actions = list(db.scalars(select(ResponseAction).order_by(ResponseAction.created_at.desc()).limit(1000)))
    confirmations = list(db.scalars(select(FamilyConfirmation).order_by(FamilyConfirmation.requested_at.desc()).limit(1000)))
    notifications = list(db.scalars(select(EmergencyNotification).order_by(EmergencyNotification.created_at.desc()).limit(500)))
    consents = list(db.scalars(select(ConsentLog).order_by(ConsentLog.created_at.desc()).limit(1000)))
    audits = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(300)))
    users = list(db.scalars(select(User).order_by(User.created_at.desc()).limit(1000)))

    senior_by_id = {item.id: item for item in seniors}
    member_by_id = {item.id: item for item in members}
    user_by_id = {item.id: item for item in users}
    voice_by_member = {item.family_member_id: item for item in voice_profiles}
    face_by_member = {item.family_member_id: item for item in face_profiles}
    samples_by_profile: dict[str, list[VoiceSample]] = {}
    for sample in voice_samples:
        samples_by_profile.setdefault(sample.voice_profile_id, []).append(sample)
    device_by_senior = {item.senior_id: item for item in devices}
    decision_by_session: dict[str, RiskDecision] = {}
    for item in decisions:
        decision_by_session.setdefault(item.call_session_id, item)
    action_by_session: dict[str, ResponseAction] = {}
    for item in actions:
        action_by_session.setdefault(item.call_session_id, item)
    confirmation_by_session: dict[str, FamilyConfirmation] = {}
    for item in confirmations:
        confirmation_by_session.setdefault(item.call_session_id, item)

    member_rows = []
    for member in members:
        voice = voice_by_member.get(member.id)
        face = face_by_member.get(member.id)
        samples = samples_by_profile.get(voice.id, []) if voice else []
        member_rows.append({
            "id": member.id, "name": _mask_name(member.name), "relation": member.relation_code or member.relation or "-",
            "phone": _mask_phone(member.phone_number_last4), "verified": member.is_verified,
            "connection_status": member.approval_status, "trust_level": member.trust_level,
            "voice_status": voice.status if voice else "NOT_REGISTERED", "voice_quality": voice.quality_score if voice else None,
            "voice_samples": len(samples), "voice_duration_ms": sum(sample.duration_ms or 0 for sample in samples),
            "face_status": face.status if face else "NOT_REGISTERED", "face_quality": face.match_score if face else None,
            "consent": bool((voice and voice.consent_id) or (face and face.consent_accepted)), "created_at": _iso(member.created_at),
        })

    senior_rows = [{
        "id": item.id, "name": _mask_name(item.name), "phone": _mask_phone(item.phone_number_last4),
        "created_at": _iso(item.created_at), "protection_status": item.protection_status,
        "device_status": device_by_senior.get(item.id).status if device_by_senior.get(item.id) else "NOT_CONNECTED",
        "family_count": sum(1 for member in members if member.family_id == item.family_id),
        "user_role": user_by_id.get(item.user_id).role if item.user_id and user_by_id.get(item.user_id) else "SENIOR",
    } for item in seniors]

    call_rows = []
    for item in sessions:
        decision = decision_by_session.get(item.id)
        action = action_by_session.get(item.id)
        confirmation = confirmation_by_session.get(item.id)
        senior = senior_by_id.get(item.senior_id)
        matched = member_by_id.get(item.matched_family_member_id) if item.matched_family_member_id else None
        call_rows.append({
            "id": item.id, "started_at": _iso(item.started_at), "ended_at": _iso(item.ended_at),
            "senior": _mask_name(senior.name if senior else None), "caller": _mask_phone(item.caller_number_last4),
            "suspected_family": _mask_name(matched.name if matched else None), "number_matched": item.family_number_matched,
            "speaker_similarity": decision.speaker_similarity if decision else None,
            "spoof_probability": decision.spoof_probability if decision else None,
            "content_risk": decision.content_risk_score if decision else None, "face_score": decision.face_match_score if decision else None,
            "family_response": confirmation.response if confirmation else (decision.family_response if decision else None),
            "risk_score": decision.risk_score if decision else 0, "risk_level": decision.risk_level if decision else "PENDING",
            "decision": decision.decision if decision else item.status, "reason_codes": decision.reason_codes.split(",") if decision and decision.reason_codes else [],
            "action": action.action if action else "NONE", "action_status": action.status if action else "-",
            "confirmation_status": confirmation.status if confirmation else "NOT_REQUESTED",
        })

    _audit(db, "ADMIN_OVERVIEW_VIEW", "ADMIN_CONSOLE", metadata={"rows": len(call_rows)})
    active_voice = sum(1 for row in member_rows if row["voice_status"] == "ENROLLED")
    active_face = sum(1 for row in member_rows if row["face_status"] == "ACTIVE")
    return {
        "metrics": {
            "seniors": len(senior_rows), "active_seniors": sum(1 for row in senior_rows if row["protection_status"] == "ACTIVE"),
            "family_members": len(member_rows), "voice_rate": round(active_voice / len(member_rows) * 100) if member_rows else 0,
            "face_rate": round(active_face / len(member_rows) * 100) if member_rows else 0,
            "calls": len(call_rows), "danger_calls": sum(1 for row in call_rows if row["risk_level"] in {"HIGH", "CRITICAL"}),
            "blocked_calls": sum(1 for row in call_rows if row["action"] in {"BLOCK", "TERMINATE"}),
            "pending_confirmations": sum(1 for row in confirmations if row.status == "PENDING"),
        },
        "seniors": senior_rows, "family_members": member_rows, "calls": call_rows,
        "actions": [{"id": row.id, "case_id": row.call_session_id, "type": row.action, "status": row.status, "failure_reason": row.failure_reason, "requested_at": _iso(row.requested_at), "executed_at": _iso(row.executed_at)} for row in actions],
        "confirmations": [{"id": row.id, "case_id": row.call_session_id, "channel": row.channel, "status": row.status, "response": row.response or "NO_RESPONSE", "requested_at": _iso(row.requested_at), "responded_at": _iso(row.responded_at)} for row in confirmations],
        "notifications": [{"id": row.id, "risk_event_id": row.risk_event_id, "status": row.status, "response": row.response, "sent_at": _iso(row.sent_at), "created_at": _iso(row.created_at)} for row in notifications],
        "consents": [{"id": row.id, "user": _mask_name(user_by_id.get(row.user_id).display_name if user_by_id.get(row.user_id) else None), "type": row.consent_type, "version": row.version, "accepted": row.accepted, "created_at": _iso(row.created_at)} for row in consents],
        "admins": [{"id": row.id, "admin_id": row.email or row.id, "name": row.display_name, "role": row.role, "created_at": _iso(row.created_at)} for row in users if row.role == "ADMIN"],
        "audits": [{"id": row.id, "actor": user_by_id.get(row.actor_user_id).email if row.actor_user_id and user_by_id.get(row.actor_user_id) else "system", "action": row.action, "resource_type": row.resource_type, "resource_id": row.resource_id, "metadata": row.metadata_json, "created_at": _iso(row.created_at)} for row in audits],
    }
