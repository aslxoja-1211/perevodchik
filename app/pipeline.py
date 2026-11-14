"""Optimized pipeline orchestrating Audio -> STT -> Translation -> TTS across languages."""

import base64
import time
from collections.abc import Callable
from typing import Any, Optional

from app.audio.pcm_utils import (
    compute_pcm16_rms,
    ensure_audio_filename_and_bytes,
    estimate_pcm16_duration_ms,
)
from app.config import Settings
from app.models.schemas import LatencyBreakdown, TranslateVoiceResponse
from app.services.stt.factory import create_stt_provider
from app.services.translation.translator import TranslationService
from app.services.tts.edge_tts_service import DEFAULT_VOICES_BY_LANG
from app.services.tts.factory import create_tts_provider


class VoiceTranslatorPipeline:
    """Orchestrates end-to-end multi-language voice translation pipeline with low latency."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.stt_provider = create_stt_provider(settings)
        self.translation_service = TranslationService(settings)
        self.tts_provider = create_tts_provider(settings)

    def _resolve_languages(
        self,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> tuple[str, str]:
        if source_lang and target_lang:
            return source_lang.lower().strip(), target_lang.lower().strip()
        if direction and "-" in direction:
            parts = direction.lower().strip().split("-", 1)
            return parts[0], parts[1]
        return "uz", "ru"

    def _resolve_tts_voice(self, target_lang: str, custom_voice: Optional[str] = None) -> str:
        if custom_voice:
            return custom_voice
        return DEFAULT_VOICES_BY_LANG.get(target_lang, self.settings.default_tts_voice)

    async def process_audio(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/pcm",
        sample_rate: int = 16000,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        direction: Optional[str] = None,
        voice: Optional[str] = None,
        rate: str = "+0%",
        on_stage_callback: Optional[Callable[[str, Any], Any]] = None,
    ) -> TranslateVoiceResponse:
        """Process incoming voice audio with progressive stage updates."""
        pipeline_start = time.perf_counter()
        src, tgt = self._resolve_languages(source_lang, target_lang, direction)
        dir_str = f"{src}-{tgt}"

        if not audio_bytes:
            return TranslateVoiceResponse(
                source_text="",
                translated_text="",
                source_lang=src,
                target_lang=tgt,
                direction=dir_str,
                audio_base64=None,
                latency=LatencyBreakdown(),
                note="Audio bo'sh.",
            )

        norm_mime = (mime_type or "audio/pcm").split(";")[0].strip().lower()
        if norm_mime in {"audio/pcm", "audio/l16"}:
            duration_ms = estimate_pcm16_duration_ms(len(audio_bytes), sample_rate=sample_rate)
            rms = compute_pcm16_rms(audio_bytes)
            if duration_ms < 120 or rms < 0.0005:
                return TranslateVoiceResponse(
                    source_text="",
                    translated_text="",
                    source_lang=src,
                    target_lang=tgt,
                    direction=dir_str,
                    audio_base64=None,
                    latency=LatencyBreakdown(total_ms=round((time.perf_counter() - pipeline_start) * 1000.0, 2)),
                    note="Sukut yoki juda qisqa audio aniqlandi.",
                )

        # Stage 1: STT
        if on_stage_callback:
            await on_stage_callback("stt_started", None)

        stt_res = await self.stt_provider.transcribe(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            sample_rate=sample_rate,
            language=src,
        )
        source_text = stt_res.text.strip()
        stt_ms = stt_res.latency_ms

        if on_stage_callback and source_text:
            await on_stage_callback("transcript_ready", source_text)

        # Stage 2: Translation
        translated_text = ""
        trans_ms = 0.0
        if source_text:
            if on_stage_callback:
                await on_stage_callback("translation_started", None)

            trans_res = await self.translation_service.translate(
                text=source_text,
                source_lang=src,
                target_lang=tgt,
            )
            translated_text = trans_res.translated_text.strip()
            trans_ms = trans_res.latency_ms

            if on_stage_callback and translated_text:
                await on_stage_callback("translation_ready", translated_text)

        # Stage 3: TTS
        audio_b64 = None
        tts_ms = 0.0
        effective_voice = self._resolve_tts_voice(tgt, voice)

        if translated_text:
            if on_stage_callback:
                await on_stage_callback("tts_started", None)

            tts_res = await self.tts_provider.synthesize(
                text=translated_text,
                voice=effective_voice,
                rate=rate,
            )
            tts_ms = tts_res.latency_ms
            if tts_res.audio_bytes:
                audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("ascii")

        total_ms = round((time.perf_counter() - pipeline_start) * 1000.0, 2)

        return TranslateVoiceResponse(
            source_text=source_text,
            translated_text=translated_text,
            source_lang=src,
            target_lang=tgt,
            direction=dir_str,
            audio_base64=audio_b64,
            audio_mime="audio/mpeg",
            latency=LatencyBreakdown(
                stt_ms=stt_ms,
                translation_ms=trans_ms,
                tts_ms=tts_ms,
                total_ms=total_ms,
            ),
            providers={
                "stt": self.stt_provider.name,
                "translation": "gemini",
                "tts": self.tts_provider.name,
                "voice": effective_voice,
            },
        )

    async def process_text(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        direction: Optional[str] = None,
        voice: Optional[str] = None,
        rate: str = "+0%",
        synthesize_audio: bool = True,
    ) -> TranslateVoiceResponse:
        """Process direct text translation and speech synthesis."""
        start = time.perf_counter()
        clean = text.strip()
        src, tgt = self._resolve_languages(source_lang, target_lang, direction)
        dir_str = f"{src}-{tgt}"

        if not clean:
            return TranslateVoiceResponse(
                source_text="",
                translated_text="",
                source_lang=src,
                target_lang=tgt,
                direction=dir_str,
                audio_base64=None,
                latency=LatencyBreakdown(),
            )

        trans_res = await self.translation_service.translate(
            text=clean,
            source_lang=src,
            target_lang=tgt,
        )
        translated_text = trans_res.translated_text
        trans_ms = trans_res.latency_ms

        audio_b64 = None
        tts_ms = 0.0
        effective_voice = self._resolve_tts_voice(tgt, voice)

        if synthesize_audio and translated_text:
            tts_res = await self.tts_provider.synthesize(
                text=translated_text,
                voice=effective_voice,
                rate=rate,
            )
            tts_ms = tts_res.latency_ms
            if tts_res.audio_bytes:
                audio_b64 = base64.b64encode(tts_res.audio_bytes).decode("ascii")

        total_ms = round((time.perf_counter() - start) * 1000.0, 2)

        return TranslateVoiceResponse(
            source_text=clean,
            translated_text=translated_text,
            source_lang=src,
            target_lang=tgt,
            direction=dir_str,
            audio_base64=audio_b64,
            audio_mime="audio/mpeg",
            latency=LatencyBreakdown(
                stt_ms=0.0,
                translation_ms=trans_ms,
                tts_ms=tts_ms,
                total_ms=total_ms,
            ),
            providers={
                "translation": trans_res.provider,
                "tts": self.tts_provider.name,
                "voice": effective_voice,
            },
            note=trans_res.note,
        )
