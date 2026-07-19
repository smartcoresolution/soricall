from uuid import uuid4

from sqlalchemy.orm import Session

from app.api.v1.auth import confirm_phone_verification, register, send_phone_verification
from app.schemas import (
    PhoneVerificationConfirmRequest,
    PhoneVerificationSendRequest,
    RegisterRequest,
)


def register_test_user(
    db: Session,
    *,
    display_name: str = "테스트 사용자",
    role: str = "GUARDIAN",
    password: str = "password123",
):
    phone_number = f"010{uuid4().int % 100_000_000:08d}"
    sent = send_phone_verification(
        PhoneVerificationSendRequest(phone_number=phone_number),
        db,
    )
    assert sent.development_code is not None
    confirmed = confirm_phone_verification(
        PhoneVerificationConfirmRequest(
            verification_id=sent.verification_id,
            code=sent.development_code,
        ),
        db,
    )
    return register(
        RegisterRequest(
            phone_number=phone_number,
            verification_token=confirmed.verification_token,
            password=password,
            display_name=display_name,
            role=role,
        ),
        db,
    )
