"""Local Faster Whisper STT provider."""

import io
import time
from typing import Optional

from app.audio.pcm_utils import ensure_audio_filename_and_bytes
from app.services.stt.base import STTProvider, STTResult

_MODEL_INSTANCE = None


def is_local_whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def get_local_whisper_model(model_name: str = "turbo", device: str = "auto", compute_type: str = "float16"):
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is None:
        from faster_whisper import WhisperModel
        effective_device = "cpu" if device == "auto" else device
        effective_compute = "int8" if effective_device == "cpu" else compute_type
        _MODEL_INSTANCE = WhisperModel(model_name, device=effective_device, compute_type=effective_compute)
    return _MODEL_INSTANCE


class LocalWhisperSTTProvider(STTProvider):
    """Offline STT using faster-whisper."""

    name = "local_whisper"
    is_mock = False

    def __init__(self, model_name: str = "turbo", device: str = "auto", compute_type: str = "float16") -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/pcm",
        sample_rate: int = 16000,
        language: str = "uz",
    ) -> STTResult:
        start = time.perf_counter()
        if not audio_bytes:
            return STTResult(text="", provider=self.name, latency_ms=0.0)

        _, payload, _ = ensure_audio_filename_and_bytes(audio_bytes, mime_type, sample_rate)
        model = get_local_whisper_model(self.model_name, self.device, self.compute_type)

        segments, _ = model.transcribe(
            io.BytesIO(payload),
            language=language if language in {"uz", "ru"} else None,
            beam_size=5,
        )
        text = " ".join([s.text for s in segments]).strip()
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        return STTResult(text=text, provider=self.name, latency_ms=latency_ms)
