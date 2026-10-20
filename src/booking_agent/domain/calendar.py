"""In-memory calendar. One booking per customer; a slot can be booked once."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

from booking_agent.domain.models import Booking, Slot


class InMemoryCalendar:
    def __init__(self, slots: list[Slot]) -> None:
        self._slots = {s.id: s for s in sorted(slots, key=lambda s: s.starts_at)}
        self._bookings: dict[str, Booking] = {}
        self._lock = threading.Lock()

    @classmethod
    def weekly(
        cls, start: datetime, days: int = 5, hours: tuple[int, ...] = (9, 11, 14, 16)
    ) -> InMemoryCalendar:
        slots = []
        for d in range(days):
            day = start + timedelta(days=d)
            for h in hours:
                at = day.replace(hour=h, minute=0, second=0, microsecond=0)
                slots.append(Slot(id=at.strftime("%Y%m%d%H%M"), starts_at=at))
        return cls(slots)

    def available(self, limit: int) -> list[Slot]:
        with self._lock:
            taken = {b.slot.id for b in self._bookings.values()}
            return [s for s in self._slots.values() if s.id not in taken][:limit]

    def reserve(self, slot_id: str, customer: str) -> Booking | None:
        with self._lock:
            slot = self._slots.get(slot_id)
            taken = {b.slot.id for b in self._bookings.values()}
            if slot is None or slot_id in taken or customer in self._bookings:
                return None
            booking = Booking(customer=customer, slot=slot)
            self._bookings[customer] = booking
            return booking

    def booking_of(self, customer: str) -> Booking | None:
        with self._lock:
            return self._bookings.get(customer)

    def cancel(self, customer: str) -> Booking | None:
        with self._lock:
            return self._bookings.pop(customer, None)
