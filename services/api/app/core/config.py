import os
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    service_name: str = "soricall-api"
    database_url: str = "sqlite:///./soricall.db"
    ai_service_url: str = "http://localhost:8100"
    ai_provider: str = "mock"
    fcm_project_id: str | None = None
    fcm_access_token: str | None = None
    jwt_secret: str = "change-me-in-production"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 14
    retain_voice_samples: bool = False
    retain_face_images: bool = False
    enrollment_delivery_backend: str = "development_link"
    sms_webhook_url: str | None = None
    sms_webhook_bearer_token: str | None = None
    sms_sender: str | None = None
    solapi_api_key: str | None = None
    solapi_api_secret: str | None = None
    device_access_token_expire_days: int = 365
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )
    rate_limit_per_minute: int = 60
    auth_rate_limit_per_minute: int = 10

    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE", ".env"), extra="ignore")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production" and self.jwt_secret == "change-me-in-production":
            raise ValueError("JWT_SECRET must be changed in production")
        if self.app_env == "production" and self.database_url.startswith("sqlite"):
            raise ValueError("production DATABASE_URL must use a managed database")
        if self.app_env == "production" and (
            not self.fcm_project_id or not self.fcm_access_token
        ):
            raise ValueError("FCM credentials must be configured in production")
        if self.app_env == "production" and self.ai_provider != "remote":
            raise ValueError("AI_PROVIDER must be remote in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
