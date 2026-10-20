from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from booking_agent.agent.graph import BookingAgent
from booking_agent.app import create_app
from booking_agent.channels.console import ConsoleSender
from booking_agent.config import Settings
from booking_agent.webhooks.dedupe import InMemoryProcessedMessages
from tests.conftest import APP_SECRET, VERIFY_TOKEN, sign, text_webhook

ANA = "15550001111"


@pytest.fixture
def sender() -> ConsoleSender:
    return ConsoleSender()


@pytest.fixture
def client(agent: BookingAgent, sender: ConsoleSender) -> TestClient:
    settings = Settings(
        whatsapp_app_secret=SecretStr(APP_SECRET), whatsapp_verify_token=SecretStr(VERIFY_TOKEN)
    )
    return TestClient(create_app(settings, agent=agent, sender=sender, processed=InMemoryProcessedMessages()))


def post(client: TestClient, body: bytes, signature: str | None) -> int:
    headers = {"content-type": "application/json"}
    if signature is not None:
        headers["x-hub-signature-256"] = signature
    return client.post("/webhook", content=body, headers=headers).status_code


def test_verification_handshake(client: TestClient) -> None:
    ok = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "12345"},
    )
    assert ok.status_code == 200 and ok.text == "12345"
    bad = client.get(
        "/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"}
    )
    assert bad.status_code == 403


def test_rejects_unsigned_or_badly_signed_requests(client: TestClient, sender: ConsoleSender) -> None:
    body = text_webhook("wamid.1", ANA, "hola")
    assert post(client, body, None) == 403
    assert post(client, body, sign(body, secret="wrong")) == 403
    assert sender.sent == []


def test_replies_to_a_signed_text_message(client: TestClient, sender: ConsoleSender) -> None:
    body = text_webhook("wamid.1", ANA, "hola")
    assert post(client, body, sign(body)) == 200
    assert len(sender.sent) == 1
    to, text = sender.sent[0]
    assert to == ANA and "asistente de Studio Demo" in text


def test_meta_retries_are_processed_once(client: TestClient, sender: ConsoleSender) -> None:
    body = text_webhook("wamid.same", ANA, "hola")
    assert post(client, body, sign(body)) == 200
    assert post(client, body, sign(body)) == 200
    assert len(sender.sent) == 1


def test_non_text_messages_get_a_short_answer(client: TestClient, sender: ConsoleSender) -> None:
    body = (
        b'{"entry":[{"changes":[{"value":{"messages":[{"id":"wamid.img","from":"'
        + ANA.encode()
        + b'","type":"image","image":{"id":"x"}}]}}]}]}'
    )
    assert post(client, body, sign(body)) == 200
    assert sender.sent == [(ANA, "Por ahora solo entiendo mensajes de texto. ¿En qué te ayudo?")]


def test_status_updates_are_acknowledged_silently(client: TestClient, sender: ConsoleSender) -> None:
    body = b'{"entry":[{"changes":[{"value":{"statuses":[{"id":"wamid.1","status":"read"}]}}]}]}'
    assert post(client, body, sign(body)) == 200
    assert sender.sent == []


def test_invalid_json_with_valid_signature_is_a_400(client: TestClient) -> None:
    body = b"not json"
    assert post(client, body, sign(body)) == 400
