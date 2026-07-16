from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.auth import confirm_phone_verification, login, register, send_phone_verification
from app.core.database import SessionLocal
from app.schemas import (
    LoginRequest,
    PhoneVerificationConfirmRequest,
    PhoneVerificationSendRequest,
    RegisterRequest,
)


def test_phone_verification_registration_and_login() -> None:
    db = SessionLocal()
    phone = f"010{uuid4().int % 100000000:08d}"
    sent = send_phone_verification(PhoneVerificationSendRequest(phone_number=phone), db)
    assert sent.development_code is not None
    confirmed = confirm_phone_verification(
        PhoneVerificationConfirmRequest(
            verification_id=sent.verification_id,
            code=sent.development_code,
        ),
        db,
    )
    auth = register(
        RegisterRequest(
            phone_number=phone,
            verification_token=confirmed.verification_token,
            password="password123",
            display_name="휴대폰 가입자",
            role="GUARDIAN",
        ),
        db,
    )
    assert auth.user.email is None
    assert auth.user.phone_number == phone
    assert login(LoginRequest(phone_number=phone, password="password123"), db).user.id == auth.user.id


def test_registration_rejects_unverified_phone() -> None:
    db = SessionLocal()
    phone = f"010{uuid4().int % 100000000:08d}"
    with pytest.raises(HTTPException) as error:
        register(
            RegisterRequest(
                phone_number=phone,
                verification_token="not-verified",
                password="password123",
                display_name="미인증 가입자",
                role="GUARDIAN",
            ),
            db,
        )
    assert error.value.detail == "phone verification required"
