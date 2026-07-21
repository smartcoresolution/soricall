import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.sms_service import send_verification_code


def test_solapi_verification_sms_uses_registered_sender() -> None:
    settings = SimpleNamespace(
        solapi_api_key="test-key",
        solapi_api_secret="test-secret",
        sms_sender="02-1234-5678",
        sms_webhook_url=None,
        sms_webhook_bearer_token=None,
        app_env="production",
    )
    response = MagicMock()
    response.read.return_value = json.dumps({
        "failedMessageList": [],
        "messageList": [{"statusCode": "2000"}],
    }).encode()
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    with patch("app.services.sms_service.get_settings", return_value=settings), patch(
        "app.services.sms_service.urlopen", return_value=response,
    ) as urlopen:
        assert send_verification_code("010-1234-5678", "654321")

    request = urlopen.call_args.args[0]
    payload = json.loads(request.data)
    assert payload["messages"][0]["to"] == "01012345678"
    assert payload["messages"][0]["from"] == "0212345678"
    assert "654321" in payload["messages"][0]["text"]
    assert request.headers["Authorization"].startswith("HMAC-SHA256 apiKey=test-key")
