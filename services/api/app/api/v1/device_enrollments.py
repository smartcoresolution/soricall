from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.security import create_access_token, hash_value, hash_verification_code, hash_phone_number, normalize_phone_number
from app.models import DeviceEnrollment, Family, PhoneVerification, Senior
from app.schemas import (
    DeviceEnrollmentResponse,
    DeviceVerificationConfirmRequest,
    DeviceVerificationRequest,
    PhoneVerificationSendResponse,
)
from app.services.sms_service import SmsDeliveryError, send_verification_code


family_router = APIRouter(prefix="/families", tags=["device-enrollments"])
public_router = APIRouter(prefix="/device-enrollments", tags=["device-enrollments"])


@family_router.post(
    "/{family_id}/protected-call-users/{protected_user_id}/device-enrollment",
    response_model=DeviceEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_device_enrollment(family_id: str, protected_user_id: str, db: DbSession) -> DeviceEnrollmentResponse:
    if not db.get(Family, family_id):
        raise HTTPException(status_code=404, detail="family not found")
    senior = db.get(Senior, protected_user_id)
    if not senior or senior.family_id != family_id:
        raise HTTPException(status_code=404, detail="protected call user not found")
    raw_token = secrets.token_urlsafe(32)
    enrollment = DeviceEnrollment(
        senior_id=senior.id,
        token_hash=hash_value(raw_token, salt="device-enrollment"),
        status="INVITED",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return _response(enrollment, senior, f"/soricall/connect?device_token={raw_token}")


@public_router.get("/resolve", response_model=DeviceEnrollmentResponse)
def resolve_device_enrollment(token: str, db: DbSession) -> DeviceEnrollmentResponse:
    enrollment, senior = _for_token(token, db)
    return _response(enrollment, senior)


@public_router.post("/verification", response_model=PhoneVerificationSendResponse, status_code=201)
def send_device_verification(token: str, request: DeviceVerificationRequest, db: DbSession) -> PhoneVerificationSendResponse:
    enrollment, senior = _for_token(token, db)
    if hash_phone_number(request.phone_number) != senior.phone_number_hash:
        raise HTTPException(status_code=400, detail="phone number does not match protected user")
    code = f"{secrets.randbelow(1_000_000):06d}"
    verification = PhoneVerification(
        phone_number=normalize_phone_number(request.phone_number),
        code_hash="pending",
        purpose=f"DEVICE_CONNECT:{enrollment.id}",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(verification)
    db.flush()
    verification.code_hash = hash_verification_code(verification.id, code)
    try:
        send_verification_code(verification.phone_number, code)
    except SmsDeliveryError as error:
        db.rollback()
        raise HTTPException(status_code=503, detail="SMS delivery is not configured or unavailable") from error
    db.commit()
    return PhoneVerificationSendResponse(
        verification_id=verification.id,
        expires_in=300,
        development_code=code if get_settings().app_env != "production" else None,
    )


@public_router.post("/verification/confirm", response_model=DeviceEnrollmentResponse)
def confirm_device_verification(token: str, request: DeviceVerificationConfirmRequest, db: DbSession) -> DeviceEnrollmentResponse:
    enrollment, senior = _for_token(token, db)
    verification = db.get(PhoneVerification, request.verification_id)
    now = datetime.now(timezone.utc)
    if not verification or verification.purpose != f"DEVICE_CONNECT:{enrollment.id}":
        raise HTTPException(status_code=404, detail="phone verification not found")
    if verification.consumed_at or _utc(verification.expires_at) <= now:
        raise HTTPException(status_code=400, detail="phone verification expired")
    verification.attempts += 1
    if verification.attempts > 5:
        db.commit()
        raise HTTPException(status_code=429, detail="phone verification attempts exceeded")
    if not secrets.compare_digest(verification.code_hash, hash_verification_code(verification.id, request.code)):
        db.commit()
        raise HTTPException(status_code=400, detail="invalid phone verification code")
    verification.consumed_at = now
    enrollment.phone_verified_at = now
    enrollment.status = "PHONE_VERIFIED"
    db.commit()
    return _response(enrollment, senior)


@public_router.post("/complete", response_model=DeviceEnrollmentResponse)
def complete_device_enrollment(token: str, db: DbSession) -> DeviceEnrollmentResponse:
    enrollment, senior = _for_token(token, db)
    if not enrollment.phone_verified_at:
        raise HTTPException(status_code=400, detail="phone verification required")
    now = datetime.now(timezone.utc)
    enrollment.permissions_confirmed_at = now
    enrollment.completed_at = now
    enrollment.status = "ACTIVE"
    senior.protection_status = "ACTIVE"
    db.commit()
    settings = get_settings()
    access_token = create_access_token(
        f"device:{enrollment.id}",
        settings.device_access_token_expire_days * 24 * 60 * 60,
        {"scope": "device", "senior_id": senior.id, "enrollment_id": enrollment.id},
    )
    return _response(enrollment, senior, access_token=access_token)


def _for_token(token: str, db: DbSession) -> tuple[DeviceEnrollment, Senior]:
    enrollment = db.scalar(select(DeviceEnrollment).where(
        DeviceEnrollment.token_hash == hash_value(token, salt="device-enrollment")
    ))
    if not enrollment:
        raise HTTPException(status_code=404, detail="device enrollment not found")
    if _utc(enrollment.expires_at) <= datetime.now(timezone.utc):
        enrollment.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=410, detail="device enrollment expired")
    senior = db.get(Senior, enrollment.senior_id)
    if not senior:
        raise HTTPException(status_code=404, detail="protected call user not found")
    return enrollment, senior


def _response(
    enrollment: DeviceEnrollment,
    senior: Senior,
    url: str | None = None,
    access_token: str | None = None,
) -> DeviceEnrollmentResponse:
    return DeviceEnrollmentResponse(
        id=enrollment.id,
        protected_user_id=senior.id,
        protected_user_name=senior.name,
        phone_number_last4=senior.phone_number_last4,
        status=enrollment.status,
        enrollment_url=url,
        access_token=access_token,
    )


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
