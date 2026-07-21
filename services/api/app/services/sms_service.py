import json
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
