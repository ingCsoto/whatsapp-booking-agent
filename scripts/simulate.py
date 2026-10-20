"""Send a signed, Meta-shaped webhook to a running agent, as WhatsApp would.

Usage: WHATSAPP_APP_SECRET=... uv run python scripts/simulate.py 15550001111 "quiero reservar"
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import uuid

import httpx

URL = os.environ.get("AGENT_URL", "http://localhost:8000/webhook")


def main() -> None:
    sender, text = sys.argv[1], " ".join(sys.argv[2:])
    body = json.dumps(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": f"wamid.{uuid.uuid4().hex}",
                                        "from": sender,
                                        "type": "text",
                                        "text": {"body": text},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ],
        }
    ).encode()
    secret = os.environ["WHATSAPP_APP_SECRET"].encode()
    signature = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    response = httpx.post(
        URL, content=body, headers={"content-type": "application/json", "x-hub-signature-256": signature}
    )
    print(response.status_code, response.text)


if __name__ == "__main__":
    main()
