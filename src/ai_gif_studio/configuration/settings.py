from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
class AppSettings(BaseSettings):
    model_config=SettingsConfigDict(env_file=".env",env_file_encoding="utf-8",extra="ignore")
    environment:str=Field("development",validation_alias="APP_ENVIRONMENT")
    log_level:str=Field("INFO",validation_alias="APP_LOG_LEVEL")
    database_url:str=Field("sqlite+aiosqlite:///./data/ai_gif_studio.db",validation_alias="APP_DATABASE_URL")
    temp_directory:Path=Field(Path("./data/tmp"),validation_alias="APP_TEMP_DIRECTORY")
    storage_directory:Path=Field(Path("./data/artifacts"),validation_alias="APP_STORAGE_DIRECTORY")
    ffmpeg_binary:str=Field("ffmpeg",validation_alias="APP_FFMPEG_BINARY")
    ffprobe_binary:str=Field("ffprobe",validation_alias="APP_FFPROBE_BINARY")
    max_upload_bytes:int=Field(52_428_800,gt=0,validation_alias="APP_MAX_UPLOAD_BYTES")
    max_duration_seconds:float=Field(60,gt=0,le=600,validation_alias="APP_MAX_DURATION_SECONDS")
    max_width:int=Field(3840,gt=0,validation_alias="APP_MAX_WIDTH")
    max_height:int=Field(2160,gt=0,validation_alias="APP_MAX_HEIGHT")
    max_queue_depth:int=Field(100,gt=0,validation_alias="APP_MAX_QUEUE_DEPTH")
    worker_timeout_seconds:int=Field(180,gt=0,validation_alias="APP_WORKER_TIMEOUT_SECONDS")
    redis_url:str=Field("redis://localhost:6379/0",validation_alias="APP_REDIS_URL")
    telegram_bot_token:str|None=Field(None,validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_allowed_user_ids:tuple[int,...]=Field((),validation_alias="TELEGRAM_ALLOWED_USER_IDS")
    @field_validator("telegram_allowed_user_ids",mode="before")
    @classmethod
    def parse_ids(cls,value:object)->tuple[int,...]:
        if value in (None,""): return ()
        if isinstance(value,str): return tuple(int(x.strip()) for x in value.split(",") if x.strip())
        return tuple(value)
@lru_cache
def get_settings()->AppSettings: return AppSettings()
