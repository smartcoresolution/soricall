import base64
import binascii
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.authorization import current_user_id
from app.models import AuditLog, DeviceKey, EnrollmentInvitation, EnrollmentQrChallenge
from app.schemas import (
    DeviceKeyRegister,
    DeviceKeyResponse,
    QrChallengeCreate,
    QrChallengeResponse,
    QrChallengeVerify,
    QrChallengeVerifyResponse,
)


device_router = APIRouter(prefix="/device-keys", tags=["device-keys"])
qr_router = APIRouter(prefix="/enrollment-invitations/qr", tags=["enrollment-qr"])


@device_router.post("", response_model=DeviceKeyResponse, status_code=status.HTTP_201_CREATED)
def register_device_key(request: DeviceKeyRegister, db: DbSession) -> DeviceKey:
    user_id = current_user_id.get()
    if not user_id:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        der = base64.b64decode(request.public_key_der_b64, validate=True)
        public_key = serialization.load_der_public_key(der)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="invalid device public key") from exc
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(
        public_key.curve, ec.SECP256R1
    ):
        raise HTTPException(status_code=400, detail="device key must use ECDSA P-256")
    fingerprint = hashlib.sha256(der).hexdigest()
    existing = db.scalar(select(DeviceKey).where(DeviceKey.fingerprint == fingerprint))
    if existing:
        if existing.user_id != user_id:
            raise HTTPException(status_code=409, detail="device key belongs to another user")
        existing.active = True
        db.commit()
        db.refresh(existing)
        return existing
    key = DeviceKey(
        user_id=user_id,
        device_id=request.device_id,
        algorithm=request.algorithm,
        public_key_der_b64=request.public_key_der_b64,
        fingerprint=fingerprint,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


@qr_router.post("/challenges", response_model=QrChallengeResponse, status_code=status.HTTP_201_CREATED)
def create_qr_challenge(request: QrChallengeCreate, db: DbSession) -> QrChallengeResponse:
    invitation = _qr_invitation(request.invitation_id, request.nonce, db)
    device_key = db.get(DeviceKey, request.device_key_id)
    if not device_key or not device_key.active:
        raise HTTPException(status_code=404, detail="active device key not found")
    challenge_value = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    challenge = EnrollmentQrChallenge(
        invitation_id=invitation.id,
        device_key_id=device_key.id,
        challenge_hash=hashlib.sha256(challenge_value.encode()).hexdigest(),
        expires_at=now + timedelta(minutes=2),
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return QrChallengeResponse(
        challenge_id=challenge.id,
        invitation_id=invitation.id,
        challenge=challenge_value,
        expires_at=challenge.expires_at,
    )


@qr_router.post("/challenges/{challenge_id}/verify", response_model=QrChallengeVerifyResponse)
def verify_qr_challenge(
    challenge_id: str,
    request: QrChallengeVerify,
    db: DbSession,
) -> QrChallengeVerifyResponse:
    challenge = db.get(EnrollmentQrChallenge, challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="QR challenge not found")
    now = datetime.now(timezone.utc)
    expires_at = challenge.expires_at if challenge.expires_at.tzinfo else challenge.expires_at.replace(tzinfo=timezone.utc)
    if challenge.verified_at or challenge.consumed_at:
        _audit_replay(db, challenge.invitation_id, "challenge_already_used")
        db.commit()
        raise HTTPException(status_code=409, detail="QR challenge already used")
    if expires_at <= now:
        raise HTTPException(status_code=410, detail="QR challenge expired")
    if not secrets.compare_digest(
        challenge.challenge_hash,
        hashlib.sha256(request.challenge.encode()).hexdigest(),
    ):
        raise HTTPException(status_code=400, detail="QR challenge mismatch")
    device_key = db.get(DeviceKey, challenge.device_key_id)
    if not device_key or not device_key.active:
        raise HTTPException(status_code=404, detail="active device key not found")
    try:
        signature = base64.b64decode(request.signature_b64, validate=True)
        public_key = serialization.load_der_public_key(
            base64.b64decode(device_key.public_key_der_b64, validate=True)
        )
        public_key.verify(
            signature,
            f"{challenge.invitation_id}.{request.challenge}".encode(),
            ec.ECDSA(hashes.SHA256()),
        )
    except (ValueError, binascii.Error, InvalidSignature) as exc:
        raise HTTPException(status_code=400, detail="invalid device signature") from exc
    invitation = db.get(EnrollmentInvitation, challenge.invitation_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="invitation not found")
    challenge.verified_at = now
    challenge.consumed_at = now
    invitation.device_key_id = device_key.id
    invitation.device_verified_at = now
    db.commit()
    return QrChallengeVerifyResponse(
        invitation_id=invitation.id,
        device_key_id=device_key.id,
        verified=True,
        verified_at=now,
    )


def _qr_invitation(invitation_id: str, nonce: str, db: DbSession) -> EnrollmentInvitation:
    invitation = db.get(EnrollmentInvitation, invitation_id)
    if not invitation or invitation.channel != "QR":
        raise HTTPException(status_code=404, detail="invitation not found")
    if not secrets.compare_digest(
        invitation.token_hash,
        hashlib.sha256(nonce.encode()).hexdigest(),
    ):
        raise HTTPException(status_code=404, detail="invitation not found")
    expires_at = invitation.expires_at if invitation.expires_at.tzinfo else invitation.expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="invitation expired")
    if invitation.device_verified_at or invitation.used_at or invitation.status == "COMPLETED":
        _audit_replay(db, invitation.id, "nonce_already_consumed")
        db.commit()
        raise HTTPException(status_code=409, detail="QR invitation already used")
    return invitation


def _audit_replay(db: DbSession, invitation_id: str, reason: str) -> None:
    db.add(
        AuditLog(
            actor_user_id=current_user_id.get(),
            action="QR_REPLAY_REJECTED",
            resource_type="ENROLLMENT_INVITATION",
            resource_id=invitation_id,
            metadata_json=f'{{"reason":"{reason}"}}',
        )
    )
