from __future__ import annotations

from booking_agent.webhooks.signature import verify_signature
from tests.conftest import APP_SECRET, sign

BODY = b'{"entry":[]}'
SECRET = APP_SECRET.encode()


def test_accepts_a_valid_signature() -> None:
    assert verify_signature(SECRET, BODY, sign(BODY))


def test_rejects_a_tampered_body() -> None:
    assert not verify_signature(SECRET, BODY + b" ", sign(BODY))


def test_rejects_a_signature_made_with_another_secret() -> None:
    assert not verify_signature(SECRET, BODY, sign(BODY, secret="other"))


def test_rejects_missing_or_malformed_headers() -> None:
    assert not verify_signature(SECRET, BODY, None)
    assert not verify_signature(SECRET, BODY, "")
    assert not verify_signature(SECRET, BODY, sign(BODY).removeprefix("sha256="))
    assert not verify_signature(SECRET, BODY, "sha1=" + sign(BODY).removeprefix("sha256="))


def test_non_ascii_header_is_rejected_without_raising() -> None:
    assert not verify_signature(SECRET, BODY, "sha256=ñandú")


def test_empty_secret_never_validates() -> None:
    assert not verify_signature(b"", BODY, sign(BODY, secret=""))
