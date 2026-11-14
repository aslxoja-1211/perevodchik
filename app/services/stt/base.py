"""Base interface and data contracts for Speech-to-Text providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


class STTConfigurationError(RuntimeError):
    """Raised when an STT provider is misconfigured or missing credentials."""


@dataclass(slots=True)
class STTResult:
    """Standardized result returned by all STT providers."""
    text: str
    provider: str
    is_mock: bool = False
    note: Optional[str] = None
    latency_ms: float = 0.0


class STTProvider(ABC):
    """Abstract interface for Speech-to-Text adapters."""

    name: str = "base"
    is_mock: bool = False

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/pcm",
        sample_rate: int = 16000,
        language: str = "uz",
    ) -> STTResult:
        """Transcribe audio bytes to text."""
