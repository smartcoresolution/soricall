import base64
import binascii
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, update

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.security import hash_phone_number, hash_verification_code, normalize_phone_number
from app.models import Family, FamilyMember, MediaImportSession, PhoneVerification
from app.schemas import (
    DeviceVerificationConfirmRequest, DeviceVerificationRequest, MediaImportConsent,
    MediaImportSessionCreate, MediaImportSessionResponse, MediaImportValidate,
    PhoneVerificationSendResponse,
)


router = APIRouter(prefix="/media-assets", tags=["media-assets"])

ALLOWED_MIME_TYPES = {
    "audio/wav": (20 * 1024 * 1024, (b"RIFF",)),
    "audio/mpeg": (20 * 1024 * 1024, (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")),
    "audio/ogg": (20 * 1024 * 1024, (b"OggS",)),
    "audio/mp4": (20 * 1024 * 1024, (b"\x00\x00",)),
    "image/jpeg": (10 * 1024 * 1024, (b"\xff\xd8\xff",)),
    "image/png": (10 * 1024 * 1024, (b"\x89PNG\r\n\x1a\n",)),
    "image/webp": (10 * 1024 * 1024, (b"RIFF",)),
}


@router.post("/import-sessions", response_model=MediaImportSessionResponse, status_code=status.HTTP_201_CREATED)
def create_import_session(request: MediaImportSessionCreate, db: DbSession) -> MediaImportSession:
    member = db.get(FamilyMember, request.family_member_id)
    if not db.get(Family, request.family_id) or not member or member.family_id != request.family_id:
        raise HTTPException(status_code=404, detail="family member not found")
    if request.mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="FILE_UNSUPPORTED")
    session = MediaImportSession(
        family_id=request.family_id,
        family_member_id=request.family_member_id,
        source=request.source,
        filename=request.filename,
        declared_mime_type=request.mime_type,
        status="PENDING_UPLOAD",
        trust_level="D",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/validate", response_model=MediaImportSessionResponse)
def validate_import_session(
    session_id: str,
    request: MediaImportValidate,
    db: DbSession,
) -> MediaImportSession:
    session = db.get(MediaImportSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="import session not found")
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at if session.expires_at.tzinfo else session.expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        session.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=410, detail="import session expired")
    try:
        header, encoded = request.data_url.split(",", 1)
        detected_mime = header.split(";", 1)[0].removeprefix("data:")
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="FILE_UNSUPPORTED") from exc
    rule = ALLOWED_MIME_TYPES.get(detected_mime)
    if not rule or detected_mime != session.declared_mime_type or not any(payload.startswith(prefix) for prefix in rule[1]):
        session.status = "REJECTED"
        session.failure_code = "FILE_UNSUPPORTED"
        db.commit()
        raise HTTPException(status_code=400, detail="FILE_UNSUPPORTED")
    if len(payload) > rule[0]:
        session.status = "REJECTED"
        session.failure_code = "FILE_TOO_LARGE"
        db.commit()
        raise HTTPException(status_code=413, detail="FILE_TOO_LARGE")
    if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in payload:
        session.status = "REJECTED"
        session.failure_code = "MALWARE_DETECTED"
        session.quality_status = "REJECTED"
        db.commit()
        raise HTTPException(status_code=400, detail="MALWARE_DETECTED")
    if len(payload) < 8:
        session.status = "REJECTED"
        session.failure_code = "MEDIA_TOO_SHORT"
        session.quality_status = "REJECTED"
        db.commit()
        raise HTTPException(status_code=400, detail="MEDIA_TOO_SHORT")
    digest = hashlib.sha256(payload).hexdigest()
    if db.scalar(
        select(MediaImportSession.id).where(
            MediaImportSession.family_member_id == session.family_member_id,
            MediaImportSession.content_hash == digest,
            MediaImportSession.id != session.id,
            MediaImportSession.status == "VALIDATED",
        )
    ):
        session.status = "REJECTED"
        session.failure_code = "DUPLICATE_FILE"
        db.commit()
        raise HTTPException(status_code=409, detail="DUPLICATE_FILE")
    session.detected_mime_type = detected_mime
    session.content_hash = digest
    session.size_bytes = len(payload)
    session.status = "VALIDATED"
    session.quality_status = "BASIC_VALIDATED"
    session.validated_at = now
    # External files remain D-level and cannot activate a family member alone.
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/phone-verification", response_model=PhoneVerificationSendResponse)
def send_import_phone_verification(
    session_id: str, request: DeviceVerificationRequest, db: DbSession
) -> PhoneVerificationSendResponse:
    session = db.get(MediaImportSession, session_id)
    member = db.get(FamilyMember, session.family_member_id) if session else None
    if not session or not member:
        raise HTTPException(status_code=404, detail="import session not found")
    if hash_phone_number(request.phone_number) != member.phone_number_hash:
        raise HTTPException(status_code=400, detail="phone number does not match family member")
    code = f"{secrets.randbelow(1_000_000):06d}"
    verification = PhoneVerification(
        phone_number=normalize_phone_number(request.phone_number), code_hash="pending",
        purpose=f"MEDIA_IMPORT:{session.id}",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(verification); db.flush()
    verification.code_hash = hash_verification_code(verification.id, code)
    db.commit()
    return PhoneVerificationSendResponse(
        verification_id=verification.id, expires_in=300,
        development_code=code if get_settings().app_env != "production" else None,
    )


@router.post("/{session_id}/phone-verification/confirm", response_model=MediaImportSessionResponse)
def confirm_import_phone_verification(
    session_id: str, request: DeviceVerificationConfirmRequest, db: DbSession
) -> MediaImportSession:
    session = db.get(MediaImportSession, session_id)
    verification = db.get(PhoneVerification, request.verification_id)
    now = datetime.now(timezone.utc)
    if not session or not verification or verification.purpose != f"MEDIA_IMPORT:{session_id}":
        raise HTTPException(status_code=404, detail="phone verification not found")
    if verification.consumed_at or verification.expires_at.replace(tzinfo=verification.expires_at.tzinfo or timezone.utc) <= now:
        raise HTTPException(status_code=400, detail="phone verification expired")
    if not secrets.compare_digest(verification.code_hash, hash_verification_code(verification.id, request.code)):
        raise HTTPException(status_code=400, detail="invalid phone verification code")
    verification.consumed_at = now
    session.phone_verified_at = now
    db.commit(); db.refresh(session)
    return session


@router.post("/{session_id}/consent", response_model=MediaImportSessionResponse)
def consent_import(session_id: str, request: MediaImportConsent, db: DbSession) -> MediaImportSession:
    session = db.get(MediaImportSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="import session not found")
    if session.status != "VALIDATED" or not session.phone_verified_at:
        raise HTTPException(status_code=409, detail="validated file and phone verification required")
    if not request.accepted:
        raise HTTPException(status_code=400, detail="biometric consent required")
    session.consented_at = datetime.now(timezone.utc)
    session.trust_level = "C" if session.source == "EXTERNAL_SHARE" else "D"
    member = db.get(FamilyMember, session.family_member_id)
    if member:
        member.trust_level = session.trust_level
        member.approval_status = "REVIEW_REQUIRED"
        member.is_verified = False
    db.commit(); db.refresh(session)
    return session


@router.post("/import-sessions/purge-expired")
def purge_expired_import_sessions(db: DbSession) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(MediaImportSession)
        .where(
            MediaImportSession.expires_at <= now,
            MediaImportSession.status.notin_(["PURGED"]),
        )
        .values(
            status="PURGED",
            content_hash=None,
            failure_code=None,
            quality_status="PURGED",
            purged_at=now,
        )
    )
    db.commit()
    return {"purged": int(result.rowcount or 0)}
