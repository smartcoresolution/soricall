import base64
import binascii
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Family, FamilyMember, MediaImportSession
from app.schemas import MediaImportSessionCreate, MediaImportSessionResponse, MediaImportValidate


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
    session.validated_at = now
    # External files remain D-level and cannot activate a family member alone.
    member = db.get(FamilyMember, session.family_member_id)
    if member:
        member.trust_level = "D"
        member.approval_status = "REVIEW_REQUIRED"
        member.is_verified = False
    db.commit()
    db.refresh(session)
    return session
