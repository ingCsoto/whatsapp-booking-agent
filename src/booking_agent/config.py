"""Settings from environment variables. Secrets are SecretStr so they never show up in logs or reprs."""

from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    whatsapp_app_secret: SecretStr
    whatsapp_verify_token: SecretStr
    whatsapp_access_token: SecretStr | None = None
    whatsapp_phone_number_id: str | None = None

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"

    business_name: str = "Studio Demo"
    business_hours: str = "lunes a viernes, de 9:00 a 18:00"
