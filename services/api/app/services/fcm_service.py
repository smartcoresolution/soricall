from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class PushResult:
    sent: bool
    message_id: str | None = None
    error: str | None = None


class FcmService:
    def send(self, *, token: str, title: str, body: str, data: dict[str, str]) -> PushResult:
        settings = get_settings()
        if not settings.fcm_project_id or not settings.fcm_access_token:
            return PushResult(sent=False, error="FCM credentials are not configured")
        try:
            response = httpx.post(
                f"https://fcm.googleapis.com/v1/projects/{settings.fcm_project_id}/messages:send",
                headers={"Authorization": f"Bearer {settings.fcm_access_token}"},
                json={"message": {"token": token, "notification": {"title": title, "body": body}, "data": data}},
                timeout=10,
            )
            response.raise_for_status()
            return PushResult(sent=True, message_id=response.json().get("name"))
        except (httpx.HTTPError, ValueError) as exc:
            return PushResult(sent=False, error=str(exc))
