"""Plain domain types. No framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

_DAYS_ES = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
_MONTHS_ES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


class Intent(StrEnum):
    GREETING = "greeting"
    BOOK = "book"
    CHOOSE_SLOT = "choose_slot"
    MY_BOOKING = "my_booking"
    CANCEL = "cancel"
    HOURS = "hours"
    HUMAN = "human"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Slot:
    id: str
    starts_at: datetime

    def label(self) -> str:
        """Spanish label independent of the server locale, e.g. "mié 21 oct · 11:00"."""
        day = _DAYS_ES[self.starts_at.weekday()]
        month = _MONTHS_ES[self.starts_at.month - 1]
        return f"{day} {self.starts_at.day} {month} · {self.starts_at:%H:%M}"


@dataclass(frozen=True, slots=True)
class Booking:
    customer: str
    slot: Slot


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    message_id: str
    sender: str
    text: str | None
