from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from app.api.deps import DbSession
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_refresh_token, verify_password
from app.core.config import get_settings
from app.models import RefreshToken, User
from app.schemas import AuthResponse, LoginRequest, RefreshTokenRequest, RegisterRequest, UserPublic


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: DbSession) -> AuthResponse:
    existing = db.scalar(select(User).where(User.email == request.email))
    if existing:
        raise HTTPException(status_code=409, detail="email already registered")

    user = User(
        email=request.email,
        phone_number=request.phone_number,
        display_name=request.display_name,
        role=request.role,
        password_hash=hash_password(request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return _auth_response(user, db)


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, db: DbSession) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == request.email))
    if not user or not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")

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
    return AuthResponse(
        access_token=create_access_token(user.id, settings.jwt_access_token_expire_minutes * 60),
        refresh_token=raw_refresh,
        user=UserPublic.model_validate(user),
    )


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
