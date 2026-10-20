"""Remembers processed message ids. Meta retries deliveries, so the same message can arrive twice."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Callable


class InMemoryProcessedMessages:
    def __init__(
        self,
        ttl_seconds: float = 86_400,
        max_items: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_items
        self._clock = clock
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def first_time(self, message_id: str) -> bool:
        now = self._clock()
        with self._lock:
            while self._seen:
                oldest_id, seen_at = next(iter(self._seen.items()))
                if now - seen_at < self._ttl and len(self._seen) < self._max:
                    break
                self._seen.pop(oldest_id)
            if message_id in self._seen:
                return False
            self._seen[message_id] = now
            return True
