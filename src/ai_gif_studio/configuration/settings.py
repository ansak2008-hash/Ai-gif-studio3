from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Central application configuration, sourced from environment and `.env`."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development", validation_alias="APP_ENVIRONMENT")
    log_level: str = Field(default="INFO", validation_alias="APP_LOG_LEVEL")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/ai_gif_studio.db", validation_alias="APP_DATABASE_URL"
    )
    temp_directory: Path = Field(default=Path("./data/tmp"), validation_alias="APP_TEMP_DIRECTORY")
    max_upload_bytes: int = Field(default=52_428_800, gt=0, validation_alias="APP_MAX_UPLOAD_BYTES")
    ffmpeg_binary: str = Field(default="ffmpeg", validation_alias="APP_FFMPEG_BINARY")
    telegram_bot_token: str | None = Field(default=None, validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_user_ids: tuple[int, ...] = Field(
        default=(), validation_alias="TELEGRAM_ALLOWED_USER_IDS"
    )

    @field_validator("telegram_allowed_user_ids", mode="before")
    @classmethod
    def parse_allowed_user_ids(cls, value: object) -> tuple[int, ...]:
        if value in (None, ""):
            return ()
        if isinstance(value, str):
            return tuple(int(item.strip()) for item in value.split(",") if item.strip())
        return tuple(value)  # type: ignore[arg-type]


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
