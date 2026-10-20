"""WhatsApp Cloud API adapter: parse incoming webhooks and send text replies."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import SecretStr

from booking_agent.domain.models import IncomingMessage

GRAPH_URL = "https://graph.facebook.com"


def parse_incoming(payload: dict[str, Any]) -> list[IncomingMessage]:
    """Extract customer messages. Status updates (sent, delivered, read) carry no messages and are ignored."""
    messages: list[IncomingMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                text = msg.get("text", {}).get("body") if msg.get("type") == "text" else None
                messages.append(IncomingMessage(message_id=msg["id"], sender=msg["from"], text=text))
    return messages


class WhatsAppCloudSender:
    def __init__(
        self,
        client: httpx.Client,
        phone_number_id: str,
        access_token: SecretStr,
        api_version: str = "v21.0",
    ) -> None:
        self._client = client
        self._url = f"{GRAPH_URL}/{api_version}/{phone_number_id}/messages"
        self._token = access_token

    def send_text(self, to: str, body: str) -> None:
        response = self._client.post(
            self._url,
            headers={"Authorization": f"Bearer {self._token.get_secret_value()}"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body}},
            timeout=10,
        )
        response.raise_for_status()
