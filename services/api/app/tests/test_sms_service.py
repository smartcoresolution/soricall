import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.sms_service import send_verification_code


def test_verification_sms_uses_configured_webhook() -> None:
    settings = SimpleNamespace(
        sms_sender="02-1234-5678",
        sms_webhook_url="https://sms.example.test/send",
        sms_webhook_bearer_token="test-token",
        app_env="production",
    )
    response = MagicMock()
    response.status = 204
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    with patch("app.services.sms_service.get_settings", return_value=settings), patch(
        "app.services.sms_service.urlopen", return_value=response,
    ) as urlopen:
        assert send_verification_code("010-1234-5678", "654321")

    request = urlopen.call_args.args[0]
    payload = json.loads(request.data)
    assert payload["to"] == "010-1234-5678"
    assert payload["from"] == "02-1234-5678"
    assert "654321" in payload["text"]
    assert request.headers["Authorization"] == "Bearer test-token"
