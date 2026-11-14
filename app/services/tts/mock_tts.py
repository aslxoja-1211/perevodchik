"""Mock TTS provider for tests and offline environments."""

import time
from typing import Optional

from app.audio.pcm_utils import pcm16_to_wav
from app.services.tts.base import TTSProvider, TTSResult


class MockTTSProvider(TTSProvider):
    name = "mock"
    is_mock = True

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> TTSResult:
        start = time.perf_counter()
        # Return 0.25s of silent 16kHz PCM16 WAV
        dummy_pcm = b"\x00\x00" * 4000
        wav_bytes = pcm16_to_wav(dummy_pcm, sample_rate=16000)
        return TTSResult(
            audio_bytes=wav_bytes,
            mime_type="audio/wav",
            voice=voice or "mock-voice",
            latency_ms=round((time.perf_counter() - start) * 1000.0, 2),
            note="Mock TTS ovozi",
        )
