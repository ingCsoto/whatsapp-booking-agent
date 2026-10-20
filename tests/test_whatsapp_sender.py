from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from booking_agent.channels.whatsapp import WhatsAppCloudSender


def test_sends_a_text_message_with_the_expected_shape() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.out"}]})

    sender = WhatsAppCloudSender(
        httpx.Client(transport=httpx.MockTransport(handler)), "1234", SecretStr("tkn")
    )
    sender.send_text("15550001111", "hola")

    req = seen[0]
    assert str(req.url) == "https://graph.facebook.com/v21.0/1234/messages"
    assert req.headers["authorization"] == "Bearer tkn"
    assert json.loads(req.content) == {
        "messaging_product": "whatsapp",
        "to": "15550001111",
        "type": "text",
        "text": {"body": "hola"},
    }


def test_raises_on_api_errors() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"error": {}})))
    with pytest.raises(httpx.HTTPStatusError):
        WhatsAppCloudSender(client, "1234", SecretStr("bad")).send_text("15550009999", "hola")
