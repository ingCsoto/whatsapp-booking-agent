"""Local adapter: prints replies instead of calling Meta. Used when no WhatsApp credentials are set."""

from __future__ import annotations

import sys


class ConsoleSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_text(self, to: str, body: str) -> None:
        self.sent.append((to, body))
        print(f"[whatsapp → {to}] {body}", file=sys.stdout, flush=True)
