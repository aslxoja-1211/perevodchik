"""Pydantic schemas for request/response payloads in Ovozli Tarjimon."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class LanguageItem(BaseModel):
    """Supported language representation."""
    code: str
    name: str
    flag: str
    default_voice: str


class LatencyBreakdown(BaseModel):
    """Detailed latency measurement across pipeline stages."""
    stt_ms: float = 0.0
    translation_ms: float = 0.0
    tts_ms: float = 0.0
    total_ms: float = 0.0


class VoiceItem(BaseModel):
    """Voice option description for speech synthesis."""
    id: str
    name: str
    gender: str
    language: str
    description: str


class TranslateTextRequest(BaseModel):
    """Request schema for text-only translation and voice synthesis."""
    text: str = Field(..., min_length=1, description="Tarjima qilinadigan matn")
    source_lang: Optional[str] = Field(default=None, description="Masalan: 'uz', 'ru', 'en', 'zh', 'tr'")
    target_lang: Optional[str] = Field(default=None, description="Masalan: 'ru', 'uz', 'en', 'zh', 'tr'")
    direction: Optional[str] = Field(default=None, description="Ixtiyoriy yo'nalish (masalan: 'uz-tr', 'uz-ru')")
    voice: Optional[str] = Field(default=None, description="TTS ovoz nomi")
    rate: Optional[str] = Field(default="+0%", description="Tezlik (masalan +10%, -10%)")
    synthesize_audio: bool = Field(default=True, description="Ovoz hosil qilish kerakmi")

    def resolve_languages(self) -> tuple[str, str]:
        if self.source_lang and self.target_lang:
            return self.source_lang.lower().strip(), self.target_lang.lower().strip()
        if self.direction and "-" in self.direction:
            parts = self.direction.lower().strip().split("-", 1)
            return parts[0], parts[1]
        return "uz", "ru"


class TranslateVoiceResponse(BaseModel):
    """Comprehensive response for voice-to-voice translation."""
    source_text: str = Field(..., description="Eshitilgan asl matn")
    translated_text: str = Field(..., description="Tarjima qilingan matn")
    source_lang: str = Field(default="uz", description="Asl til kodi")
    target_lang: str = Field(default="ru", description="Tarjima tili kodi")
    direction: str = Field(default="uz-ru", description="Tarjima yo'nalishi (masalan: 'uz-tr')")
    audio_base64: Optional[str] = Field(default=None, description="MP3 audioning base64 kodi")
    audio_mime: str = "audio/mpeg"
    latency: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    providers: dict[str, str] = Field(default_factory=dict)
    note: Optional[str] = None


class HealthResponse(BaseModel):
    """Service status and provider availability."""
    status: str
    app_name: str
    version: str
    active_stt: str
    active_translation: str
    active_tts: str
    configured_providers: dict[str, bool]
    supported_languages: list[str] = ["uz", "ru", "en", "zh", "tr"]


class WebSocketMessage(BaseModel):
    """Inbound/outbound WebSocket payload structure."""
    type: str
    data: Optional[Any] = None
