from uuid import uuid4
from urllib.parse import parse_qs, urlparse

from app.api.v1.device_enrollments import (
    complete_device_enrollment,
    confirm_device_verification,
    create_device_enrollment,
    send_device_verification,
)
from app.core.database import Base, SessionLocal, engine
from app.core.security import decode_access_token, hash_phone_number
from app.models import Family, Senior
from app.schemas import DeviceVerificationConfirmRequest, DeviceVerificationRequest


def test_parent_device_enrollment_flow() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    phone = f"010{uuid4().int % 100000000:08d}"
    family = Family(name="기기 연결 가족")
    db.add(family)
    db.flush()
    senior = Senior(
        family_id=family.id,
        name="부모님",
        relation_code="MOTHER",
        phone_number_hash=hash_phone_number(phone),
        phone_number_last4=phone[-4:],
    )
    db.add(senior)
    db.commit()

    invited = create_device_enrollment(
        family.id,
        senior.id,
        DeviceVerificationRequest(phone_number=phone),
        db,
    )
    token = parse_qs(urlparse(invited.enrollment_url or "").query)["device_token"][0]
    sent = send_device_verification(token, DeviceVerificationRequest(phone_number=phone), db)
    verified = confirm_device_verification(
        token,
        DeviceVerificationConfirmRequest(
            verification_id=sent.verification_id,
            code=sent.development_code or "",
        ),
        db,
    )
    assert verified.status == "PHONE_VERIFIED"
    completed = complete_device_enrollment(token, db)
    assert completed.status == "ACTIVE"
    assert completed.access_token
    claims = decode_access_token(completed.access_token)
    assert claims is not None
    assert claims["scope"] == "device"
    assert claims["senior_id"] == senior.id
    assert db.get(Senior, senior.id).protection_status == "ACTIVE"
