"""Configuration settings for Ovozli Tarjimon loaded from environment."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

TranslationDirection = Literal["uz-ru", "ru-uz"]


class Settings(BaseSettings):
    """Application settings with environment variable precedence."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Ovozli Tarjimon (Voice Translator)"
    app_version: str = "1.0.0"

    # Provayder sozlamalari
    stt_provider: str = "gemini"  # auto, gemini, whisper, mock
    translation_provider: str = "gemini"  # auto, gemini, openai, mock
    tts_provider: str = "edge_tts"  # edge_tts, mock

    # Gemini
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.5-flash-lite"

    # OpenAI (Ixtiyoriy)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_stt_model: str = "whisper-1"

    # Faster Whisper (Lokal)
    local_whisper_model: str = "turbo"
    local_whisper_device: str = "auto"
    local_whisper_compute_type: str = "float16"

    # Edge-TTS
    default_tts_voice: str = "ru-RU-SvetlanaNeural"
    tts_rate: str = "+0%"
    tts_pitch: str = "+0Hz"

    # Default direction
    default_direction: TranslationDirection = "uz-ru"

    # Server sozlamalari
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
    timeout_seconds: float = 12.0
    max_audio_bytes: int = 10 * 1024 * 1024  # 10 MB

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def resolved_stt_provider(self) -> str:
        prov = self.stt_provider.lower().strip()
        if prov in {"gemini", "auto"}:
            if self.gemini_api_key:
                return "gemini"
            if self.openai_api_key:
                return "openai"
            return "mock"
        if prov == "whisper":
            if self.openai_api_key:
                return "openai"
            return "local_whisper"
        return prov

    def resolved_translation_provider(self) -> str:
        prov = self.translation_provider.lower().strip()
        if prov in {"gemini", "auto"}:
            if self.gemini_api_key:
                return "gemini"
            if self.openai_api_key:
                return "openai"
            return "mock"
        return prov

    def resolved_tts_provider(self) -> str:
        prov = self.tts_provider.lower().strip()
        if prov in {"edge_tts", "auto"}:
            return "edge_tts"
        return prov


@lru_cache
def get_settings() -> Settings:
    return Settings()
