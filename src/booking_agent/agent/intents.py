"""Deterministic intent classifier. Used offline, in tests, and as the fallback when the LLM fails."""

from __future__ import annotations

import unicodedata

from booking_agent.domain.models import Intent

# Order matters: the first match wins, so more specific intents come first
# ("cancelar mi cita" is a cancellation, not a new booking).
_RULES: tuple[tuple[Intent, tuple[str, ...]], ...] = (
    (Intent.HUMAN, ("asesor", "humano", "persona", "agente", "human", "agent")),
    (Intent.CANCEL, ("cancelar", "cancela", "anular", "cancel")),
    (Intent.MY_BOOKING, ("mi cita", "mi reserva", "cuando es", "my booking", "my appointment")),
    (Intent.BOOK, ("reservar", "reserva", "agendar", "cita", "turno", "book", "appointment")),
    (Intent.HOURS, ("horario", "abren", "cierran", "direccion", "ubicacion", "donde", "hours", "open")),
    (Intent.GREETING, ("hola", "buenas", "buenos", "hello", "hi")),
)


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).strip()


class RuleBasedClassifier:
    def classify(self, text: str) -> Intent:
        words = f" {normalize(text)} "
        for intent, keywords in _RULES:
            if any(f" {kw} " in words or (" " in kw and kw in words) for kw in keywords):
                return intent
        return Intent.UNKNOWN
