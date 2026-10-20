"""Ports: what the agent needs from the outside world. Adapters implement them."""

from __future__ import annotations

from typing import Protocol

from booking_agent.domain.models import Booking, Intent, Slot


class IntentClassifier(Protocol):
    def classify(self, text: str) -> Intent: ...


class BookingCalendar(Protocol):
    def available(self, limit: int) -> list[Slot]: ...

    def reserve(self, slot_id: str, customer: str) -> Booking | None: ...

    def booking_of(self, customer: str) -> Booking | None: ...

    def cancel(self, customer: str) -> Booking | None: ...


class MessageSender(Protocol):
    def send_text(self, to: str, body: str) -> None: ...


class ProcessedMessages(Protocol):
    def first_time(self, message_id: str) -> bool:
        """Return True the first time an id is seen, False for every repeat."""
        ...
