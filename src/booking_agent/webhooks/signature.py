"""Meta webhook signature check. Pure function, fail-closed."""

from __future__ import annotations

import hashlib
import hmac

_PREFIX = "sha256="


def verify_signature(app_secret: bytes, body: bytes, header: str | None) -> bool:
    """Validate ``X-Hub-Signature-256`` against the raw request body.

    Returns False (never raises) for a missing, malformed or non-ASCII header, so a hostile header
    cannot turn into a 500. The comparison is constant-time.
    """
    if not app_secret or not header or not header.startswith(_PREFIX):
        return False
    try:
        received = header[len(_PREFIX) :].encode("ascii")
    except UnicodeEncodeError:
        return False
    expected = hmac.new(app_secret, body, hashlib.sha256).hexdigest().encode("ascii")
    return hmac.compare_digest(expected, received)
