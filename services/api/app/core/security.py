import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.core.config import get_settings


def hash_value(value: str, *, salt: str = "") -> str:
    payload = f"{salt}:{value}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def hash_password(password: str) -> str:
    return hash_value(password, salt="password")


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def hash_safe_word(word: str) -> str:
    return hash_value(word.strip().lower(), salt="safe-word")


def hash_phone_number(phone_number: str) -> str:
    normalized = normalize_phone_number(phone_number)
    return hash_value(normalized, salt="phone-number")


def normalize_phone_number(phone_number: str) -> str:
    return "".join(ch for ch in phone_number if ch.isdigit() or ch == "+")


def phone_last4(phone_number: str) -> str:
    digits = "".join(ch for ch in phone_number if ch.isdigit())
    return digits[-4:]


def create_access_token(subject: str, expires_in_seconds: int = 3600) -> str:
    settings = get_settings()
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": subject, "exp": int(time.time()) + expires_in_seconds}
    signing_input = ".".join([_b64_json(header), _b64_json(payload)])
    signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64(signature)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        signing_input, signature = token.rsplit(".", 1)
        expected = hmac.new(
            settings.jwt_secret.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_b64(expected), signature):
            return None
        payload_raw = _b64_decode(signing_input.split(".")[1])
        payload = json.loads(payload_raw)
    except (ValueError, json.JSONDecodeError, IndexError):
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def _b64_json(value: dict[str, Any]) -> str:
    return _b64(json.dumps(value, separators=(",", ":")).encode("utf-8"))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)

