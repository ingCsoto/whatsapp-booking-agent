from __future__ import annotations

from booking_agent.webhooks.dedupe import InMemoryProcessedMessages


def test_repeats_are_detected_until_the_ttl_expires() -> None:
    now = [0.0]
    seen = InMemoryProcessedMessages(ttl_seconds=60, clock=lambda: now[0])
    assert seen.first_time("a")
    assert not seen.first_time("a")
    now[0] = 61
    assert seen.first_time("a")


def test_memory_is_bounded() -> None:
    seen = InMemoryProcessedMessages(max_items=2, clock=lambda: 0.0)
    for mid in ("a", "b", "c"):
        assert seen.first_time(mid)
    assert seen.first_time("a")  # evicted, so it counts as new again
