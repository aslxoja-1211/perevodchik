"""Mock STT provider for offline testing and development."""

import time
from app.services.stt.base import STTProvider, STTResult


class MockSTTProvider(STTProvider):
    name = "mock"
    is_mock = True

    def __init__(self, demo_text: str = "Assalomu alaykum, bugun ob-havo juda yaxshi.") -> None:
        self.demo_text = demo_text

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/pcm",
        sample_rate: int = 16000,
        language: str = "uz",
    ) -> STTResult:
        start = time.perf_counter()
        text = "Здравствуйте, хорошая сегодня погода." if language == "ru" else self.demo_text
        return STTResult(
            text=text,
            provider=self.name,
            is_mock=True,
            note="Mock STT rejimi",
            latency_ms=round((time.perf_counter() - start) * 1000.0, 2),
        )
