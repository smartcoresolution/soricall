from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
import secrets

from app.api.deps import DbSession
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_phone_number, hash_refresh_token, hash_verification_code, normalize_phone_number, phone_last4, verify_password
from app.core.config import get_settings
from app.models import Family, PhoneVerification, RefreshToken, Senior, User
from app.schemas import AuthResponse, LoginRequest, PhoneVerificationConfirmRequest, PhoneVerificationConfirmResponse, PhoneVerificationSendRequest, PhoneVerificationSendResponse, RefreshTokenRequest, RegisterRequest, UserPublic


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/phone-verifications", response_model=PhoneVerificationSendResponse, status_code=status.HTTP_201_CREATED)
def send_phone_verification(request: PhoneVerificationSendRequest, db: DbSession) -> PhoneVerificationSendResponse:
    phone_number = normalize_phone_number(request.phone_number)
    if db.scalar(select(User).where(User.phone_number == phone_number)):
        raise HTTPException(status_code=409, detail="phone number already registered")
    code = f"{secrets.randbelow(1_000_000):06d}"
    verification = PhoneVerification(
        phone_number=phone_number,
        code_hash="pending",
        purpose="SIGNUP",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(verification)
    db.flush()
    verification.code_hash = hash_verification_code(verification.id, code)
    db.commit()
    return PhoneVerificationSendResponse(
        verification_id=verification.id,
        expires_in=300,
        development_code=code if get_settings().app_env != "production" else None,
    )


@router.post("/phone-verifications/confirm", response_model=PhoneVerificationConfirmResponse)
def confirm_phone_verification(request: PhoneVerificationConfirmRequest, db: DbSession) -> PhoneVerificationConfirmResponse:
    verification = db.get(PhoneVerification, request.verification_id)
    now = datetime.now(timezone.utc)
    if not verification or verification.purpose != "SIGNUP":
        raise HTTPException(status_code=404, detail="phone verification not found")
    if verification.consumed_at or _as_utc(verification.expires_at) <= now:
        raise HTTPException(status_code=400, detail="phone verification expired")
    if verification.attempts >= 5:
        raise HTTPException(status_code=429, detail="phone verification attempts exceeded")
    verification.attempts += 1
    if not secrets.compare_digest(verification.code_hash, hash_verification_code(verification.id, request.code)):
        db.commit()
        raise HTTPException(status_code=400, detail="invalid phone verification code")
    verification.verified_at = now
    token = create_refresh_token()
    verification.code_hash = hash_verification_code(verification.id, token)
    db.commit()
    return PhoneVerificationConfirmResponse(verification_token=token)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: DbSession) -> AuthResponse:
    phone_number = normalize_phone_number(request.phone_number)
    existing = db.scalar(select(User).where(User.phone_number == phone_number))
    if existing:
        raise HTTPException(status_code=409, detail="phone number already registered")

    verification = db.scalar(select(PhoneVerification).where(
        PhoneVerification.phone_number == phone_number,
        PhoneVerification.verified_at.is_not(None),
        PhoneVerification.consumed_at.is_(None),
    ).order_by(PhoneVerification.created_at.desc()))
    if not verification or _as_utc(verification.expires_at) <= datetime.now(timezone.utc) or not secrets.compare_digest(verification.code_hash, hash_verification_code(verification.id, request.verification_token)):
        raise HTTPException(status_code=400, detail="phone verification required")

    user = User(
        email=None,
        phone_number=phone_number,
        display_name=request.display_name,
        role=request.role,
        password_hash=hash_password(request.password),
    )
    verification.consumed_at = datetime.now(timezone.utc)
    db.add(user)
    db.flush()
    if request.role == "SENIOR":
        family = Family(
            name=f"{request.display_name}님의 통화보호 가족",
            created_by=user.id,
        )
        db.add(family)
        db.flush()
        db.add(
            Senior(
                family_id=family.id,
                user_id=user.id,
                name=request.display_name,
                member_type="PROTECTED_CALL_USER",
                relation_code="SELF",
                protection_status="PREPARING",
                phone_number_hash=hash_phone_number(phone_number),
                phone_number_last4=phone_last4(phone_number),
            )
        )

    return _auth_response(user, db)


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, db: DbSession) -> AuthResponse:
    user = db.scalar(select(User).where(User.phone_number == normalize_phone_number(request.phone_number)))
    if not user or not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid phone number or password")

    return _auth_response(user, db)


@router.post("/refresh", response_model=AuthResponse)
def refresh_access_token(request: RefreshTokenRequest, db: DbSession) -> AuthResponse:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(request.refresh_token)))
    now = datetime.now(timezone.utc)
    if not stored or stored.revoked_at is not None or _as_utc(stored.expires_at) <= now:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    user = db.get(User, stored.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    stored.revoked_at = now
    db.commit()
    return _auth_response(user, db)


def _auth_response(user: User, db) -> AuthResponse:
    settings = get_settings()
    raw_refresh = create_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days),
    ))
    db.commit()
    senior = db.scalar(
        select(Senior)
        .where(Senior.user_id == user.id, Senior.relation_code == "SELF")
        .order_by(Senior.created_at)
    )
    return AuthResponse(
        access_token=create_access_token(user.id, settings.jwt_access_token_expire_minutes * 60),
        refresh_token=raw_refresh,
        user=UserPublic.model_validate(user),
        family_id=senior.family_id if senior else None,
        senior_id=senior.id if senior else None,
    )


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
