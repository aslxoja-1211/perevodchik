"""Factory for instantiating configured STT providers."""

from app.config import Settings
from app.services.stt.base import STTProvider
from app.services.stt.gemini_stt import GeminiSTTProvider
from app.services.stt.local_whisper import LocalWhisperSTTProvider, is_local_whisper_available
from app.services.stt.mock_stt import MockSTTProvider


def create_stt_provider(settings: Settings, provider_override: str | None = None) -> STTProvider:
    choice = (provider_override or settings.resolved_stt_provider()).lower().strip()

    if choice == "gemini":
        if settings.gemini_api_key:
            return GeminiSTTProvider(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
                timeout_ms=int(settings.timeout_seconds * 1000),
            )
        choice = "mock"

    if choice == "local_whisper":
        if is_local_whisper_available():
            return LocalWhisperSTTProvider(
                model_name=settings.local_whisper_model,
                device=settings.local_whisper_device,
                compute_type=settings.local_whisper_compute_type,
            )
        choice = "mock"

    return MockSTTProvider()
