"""Factory for instantiating configured TTS providers."""

from app.config import Settings
from app.services.tts.base import TTSProvider
from app.services.tts.edge_tts_service import EdgeTTSProvider
from app.services.tts.mock_tts import MockTTSProvider


def create_tts_provider(settings: Settings, provider_override: str | None = None) -> TTSProvider:
    choice = (provider_override or settings.resolved_tts_provider()).lower().strip()

    if choice == "edge_tts":
        return EdgeTTSProvider(default_voice=settings.default_tts_voice)

    return MockTTSProvider()
