"""HTTP surface: Meta's verification handshake and the message webhook."""

from __future__ import annotations

import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import SecretStr

from booking_agent.agent.graph import BookingAgent
from booking_agent.channels.whatsapp import parse_incoming
from booking_agent.domain.models import IncomingMessage
from booking_agent.domain.ports import MessageSender, ProcessedMessages
from booking_agent.webhooks.signature import verify_signature

log = logging.getLogger(__name__)

NON_TEXT_REPLY = "Por ahora solo entiendo mensajes de texto. ¿En qué te ayudo?"


def build_router(
    app_secret: SecretStr,
    verify_token: SecretStr,
    agent: BookingAgent,
    sender: MessageSender,
    processed: ProcessedMessages,
) -> APIRouter:
    router = APIRouter()

    @router.get("/webhook", response_class=PlainTextResponse)
    def verify(
        mode: str = Query("", alias="hub.mode"),
        token: str = Query("", alias="hub.verify_token"),
        challenge: str = Query("", alias="hub.challenge"),
    ) -> str:
        expected = verify_token.get_secret_value().encode()
        if mode == "subscribe" and hmac.compare_digest(token.encode(), expected):
            return challenge
        raise HTTPException(status_code=403, detail="verification failed")

    @router.post("/webhook")
    async def receive(request: Request, background: BackgroundTasks) -> dict[str, str]:
        body = await request.body()
        secret = app_secret.get_secret_value().encode()
        if not verify_signature(secret, body, request.headers.get("x-hub-signature-256")):
            raise HTTPException(status_code=403, detail="invalid signature")
        try:
            payload = json.loads(body)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid JSON") from exc
        for message in parse_incoming(payload):
            if processed.first_time(message.message_id):
                background.add_task(handle, message)
        return {"status": "ok"}  # answer fast; Meta retries slow webhooks

    def handle(message: IncomingMessage) -> None:
        try:
            reply = NON_TEXT_REPLY if message.text is None else agent.reply(message.sender, message.text)
            if reply:
                sender.send_text(message.sender, reply)
        except Exception:
            log.exception("failed to handle message %s", message.message_id)

    return router
