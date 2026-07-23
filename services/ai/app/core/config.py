import os
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    service_name: str = "soricall-ai"
    speaker_provider: str = "mock"
    anti_spoof_provider: str = "mock"
    stt_provider: str = "mock"
    nlp_provider: str = "rules"

    model_config = SettingsConfigDict(env_file=os.getenv("ENV_FILE", ".env"), extra="ignore")

    @model_validator(mode="after")
    def reject_mock_production(self) -> "Settings":
        if self.app_env == "production" and "mock" in {
            self.speaker_provider,
            self.anti_spoof_provider,
            self.stt_provider,
        }:
            raise ValueError("production AI providers must use evaluated real models")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
