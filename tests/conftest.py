from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import Any

import pytest

from booking_agent.agent.graph import BookingAgent
from booking_agent.agent.intents import RuleBasedClassifier
from booking_agent.domain.calendar import InMemoryCalendar

APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"


@pytest.fixture
def calendar() -> InMemoryCalendar:
    return InMemoryCalendar.weekly(datetime(2026, 3, 2), days=1, hours=(9, 11, 14, 16))


@pytest.fixture
def agent(calendar: InMemoryCalendar) -> BookingAgent:
    return BookingAgent(RuleBasedClassifier(), calendar, "Studio Demo", "lunes a viernes, de 9:00 a 18:00")


def sign(body: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def text_webhook(message_id: str, sender: str, text: str) -> bytes:
    payload: dict[str, Any] = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"id": message_id, "from": sender, "type": "text", "text": {"body": text}}
                            ]
                        }
                    }
                ]
            }
        ],
    }
    return json.dumps(payload).encode()
