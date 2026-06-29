from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserPublic


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

    return AuthResponse(access_token=create_access_token(user.id), user=UserPublic.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest, db: DbSession) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == request.email))
    if not user or not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")

    return AuthResponse(access_token=create_access_token(user.id), user=UserPublic.model_validate(user))

