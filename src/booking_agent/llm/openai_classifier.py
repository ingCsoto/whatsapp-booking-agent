"""LLM intent classifier with structured output and a deterministic fallback."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from booking_agent.domain.models import Intent
from booking_agent.domain.ports import IntentClassifier

log = logging.getLogger(__name__)

PROMPT_VERSION = "intent-v1"
SYSTEM_PROMPT = (
    "You classify one WhatsApp message sent to a small business that takes appointments. "
    "Answer with the single intent that best matches the customer's goal. "
    "Use 'choose_slot' only when the message picks one of several offered time slots. "
    "Use 'unknown' when no intent clearly applies."
)
_SCHEMA = {
    "type": "object",
    "properties": {"intent": {"type": "string", "enum": [i.value for i in Intent]}},
    "required": ["intent"],
    "additionalProperties": False,
}


class OpenAIIntentClassifier:
    """Calls the model with a strict JSON schema. Any failure (timeout, refusal, bad JSON, unknown
    label) degrades to the rule-based classifier instead of breaking the conversation."""

    def __init__(self, create: Callable[..., Any], model: str, fallback: IntentClassifier) -> None:
        self._create = create
        self._model = model
        self._fallback = fallback

    def classify(self, text: str) -> Intent:
        try:
            response = self._create(
                model=self._model,
                temperature=0,
                timeout=8,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "intent", "strict": True, "schema": _SCHEMA},
                },
            )
            content = response.choices[0].message.content
            return Intent(json.loads(content)["intent"])
        except Exception:
            log.warning("intent classification fell back to rules", extra={"prompt_version": PROMPT_VERSION})
            return self._fallback.classify(text)
