import json
import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings


class SmsDeliveryError(RuntimeError):
    pass


def send_verification_code(phone_number: str, code: str) -> bool:
    """Deliver through an operator-owned HTTPS webhook.

    Expected JSON body: {"to", "from", "text"}. Any 2xx response is success.
    Development without a webhook keeps exposing development_code to callers.
    """
    settings = get_settings()
    if settings.solapi_api_key and settings.solapi_api_secret and settings.sms_sender:
        return _send_solapi(
            phone_number,
            settings.sms_sender,
            code,
            settings.solapi_api_key,
            settings.solapi_api_secret,
        )
    if not settings.sms_webhook_url:
        if settings.app_env == "production":
            raise SmsDeliveryError("SMS_WEBHOOK_URL is not configured")
        return False

    body = json.dumps({
        "to": phone_number,
        "from": settings.sms_sender,
        "text": f"[SoriCall] 휴대전화 인증번호는 {code}입니다. 5분 안에 입력해 주세요.",
    }).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if settings.sms_webhook_bearer_token:
        headers["Authorization"] = f"Bearer {settings.sms_webhook_bearer_token}"
    request = Request(settings.sms_webhook_url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            if not 200 <= response.status < 300:
                raise SmsDeliveryError(f"SMS webhook returned HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError) as error:
        raise SmsDeliveryError("SMS delivery failed") from error
    return True


def _send_solapi(phone_number: str, sender: str, code: str, api_key: str, api_secret: str) -> bool:
    date = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    salt = secrets.token_hex(16)
    signature = hmac.new(
        api_secret.encode("utf-8"),
        f"{date}{salt}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    body = json.dumps({"messages": [{
        "to": _digits(phone_number),
        "from": _digits(sender),
        "text": f"[SoriCall] 인증번호는 {code}입니다. 5분 안에 입력해 주세요.",
        "type": "SMS",
        "autoTypeDetect": False,
    }]}).encode("utf-8")
    request = Request(
        "https://api.solapi.com/messages/v4/send-many/detail",
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": (
                f"HMAC-SHA256 apiKey={api_key}, date={date}, "
                f"salt={salt}, signature={signature}"
            ),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise SmsDeliveryError("SOLAPI delivery failed") from error
    if result.get("failedMessageList") or not result.get("messageList"):
        raise SmsDeliveryError("SOLAPI rejected the message")
    return True


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())
