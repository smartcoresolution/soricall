from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.auth import admin_login, confirm_phone_verification, login, register, send_phone_verification
from app.core.database import SessionLocal
from app.models import Family, Senior, User
from app.schemas import (
    AdminLoginRequest,
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


def test_senior_registration_creates_self_protection_context() -> None:
    db = SessionLocal()
    phone = f"010{uuid4().int % 100000000:08d}"
    sent = send_phone_verification(PhoneVerificationSendRequest(phone_number=phone), db)
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
            display_name="어르신 사용자",
            role="SENIOR",
        ),
        db,
    )

    assert auth.family_id is not None
    assert auth.senior_id is not None
    family = db.get(Family, auth.family_id)
    senior = db.get(Senior, auth.senior_id)
    assert family is not None
    assert family.created_by == auth.user.id
    assert senior is not None
    assert senior.family_id == family.id
    assert senior.user_id == auth.user.id
    assert senior.relation_code == "SELF"
    assert senior.phone_number_last4 == phone[-4:]
    assert login(LoginRequest(phone_number=phone, password="password123"), db).senior_id == senior.id
    db.close()


def test_admin_login_only_accepts_admin_role() -> None:
    db = SessionLocal()
    admin_phone = f"010{uuid4().int % 100000000:08d}"
    sent = send_phone_verification(PhoneVerificationSendRequest(phone_number=admin_phone), db)
    confirmed = confirm_phone_verification(PhoneVerificationConfirmRequest(verification_id=sent.verification_id, code=sent.development_code), db)
    admin = register(RegisterRequest(phone_number=admin_phone, verification_token=confirmed.verification_token, password="password123", display_name="운영 관리자", role="ADMIN"), db)
    admin_user = db.get(User, admin.user.id)
    admin_user.email = "admin-test"
    db.commit()
    assert admin_login(AdminLoginRequest(admin_id="admin-test", password="password123"), db).user.id == admin.user.id

    user_phone = f"010{uuid4().int % 100000000:08d}"
    user_sent = send_phone_verification(PhoneVerificationSendRequest(phone_number=user_phone), db)
    user_confirmed = confirm_phone_verification(PhoneVerificationConfirmRequest(verification_id=user_sent.verification_id, code=user_sent.development_code), db)
    regular = register(RegisterRequest(phone_number=user_phone, verification_token=user_confirmed.verification_token, password="password123", display_name="일반 사용자", role="GUARDIAN"), db)
    regular_user = db.get(User, regular.user.id)
    regular_user.email = "regular-test"
    db.commit()
    with pytest.raises(HTTPException) as error:
        admin_login(AdminLoginRequest(admin_id="regular-test", password="password123"), db)
    assert error.value.detail == "invalid admin credentials"
    db.close()
