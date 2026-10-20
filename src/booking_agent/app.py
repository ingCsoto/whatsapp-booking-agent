"""Application factory. Run with: uvicorn booking_agent.app:create_app --factory"""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx
from fastapi import FastAPI

from booking_agent.agent.graph import BookingAgent
from booking_agent.agent.intents import RuleBasedClassifier
from booking_agent.channels.console import ConsoleSender
from booking_agent.channels.whatsapp import WhatsAppCloudSender
from booking_agent.config import Settings
from booking_agent.domain.calendar import InMemoryCalendar
from booking_agent.domain.ports import IntentClassifier, MessageSender, ProcessedMessages
from booking_agent.webhooks.dedupe import InMemoryProcessedMessages
from booking_agent.webhooks.routes import build_router


def _classifier(settings: Settings) -> IntentClassifier:
    rules = RuleBasedClassifier()
    if settings.openai_api_key is None:
        return rules
    from openai import OpenAI

    from booking_agent.llm.openai_classifier import OpenAIIntentClassifier

    client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
    return OpenAIIntentClassifier(client.chat.completions.create, settings.openai_model, fallback=rules)


def _sender(settings: Settings) -> MessageSender:
    if settings.whatsapp_access_token and settings.whatsapp_phone_number_id:
        return WhatsAppCloudSender(
            httpx.Client(), settings.whatsapp_phone_number_id, settings.whatsapp_access_token
        )
    return ConsoleSender()


def create_app(
    settings: Settings | None = None,
    *,
    agent: BookingAgent | None = None,
    sender: MessageSender | None = None,
    processed: ProcessedMessages | None = None,
) -> FastAPI:
    settings = settings or Settings()  # values come from the environment
    tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    agent = agent or BookingAgent(
        classifier=_classifier(settings),
        calendar=InMemoryCalendar.weekly(tomorrow),
        business_name=settings.business_name,
        business_hours=settings.business_hours,
    )
    app = FastAPI(title="WhatsApp booking agent")
    app.include_router(
        build_router(
            app_secret=settings.whatsapp_app_secret,
            verify_token=settings.whatsapp_verify_token,
            agent=agent,
            sender=sender or _sender(settings),
            processed=processed or InMemoryProcessedMessages(),
        )
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
