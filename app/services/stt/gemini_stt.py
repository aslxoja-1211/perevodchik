"""Google Gemini multimodal Speech-to-Text adapter supporting multiple languages."""

import time
from google.genai import types

from app.audio.pcm_utils import (
    compute_pcm16_rms,
    ensure_audio_filename_and_bytes,
    estimate_pcm16_duration_ms,
)
from app.services.gemini_client import (
    create_gemini_client,
    generate_with_failover,
    ordered_gemini_models,
    thinking_config_for_model,
)
from app.services.stt.base import STTProvider, STTResult

STT_PROMPTS_BY_LANG: dict[str, str] = {
    "uz": (
        "Ushbu audiodagi nutqni aniq transkripsiya qiling. O'zbekcha bo'lsa lotin yozuvida (o', g', sh, ch bilan), "
        "agar turkcha yoki boshqa tilda gapirilgan bo'lsa, aynan gapirilgan tilda va yozuvda yozing. "
        "Faqat aytilgan matnni qaytaring, qo'shimcha izoh yozmang. "
        "Agar audio bo'sh yoki faqat sukut bo'lsa, bo'sh satr qaytaring."
    ),
    "tr": (
        "Bu sesteki konuşmayı doğru ve eksiksiz bir şekilde yazıya dökün. "
        "Türkçe ise Türkçe olarak, başka bir dilde ise konuşulan dilde transkript edin. "
        "Yalnızca konuşulan metni döndürün, tırnak işareti veya ek açıklama eklemeyin. "
        "Ses boş veya sessizse sadece boş dize döndürün."
    ),
    "ru": (
        "Сделайте точную транскрипцию речи из этого аудио. "
        "Если речь на русском — пишите по-русски, если на турецком или другом языке — пишите на языке оригинала. "
        "Верните только распознанный текст без каких-либо комментариев и кавычек. "
        "Если аудио пустое или содержит только тишину, верните пустую строку."
    ),
    "en": (
        "Transcribe the speech in this audio accurately in its spoken language. "
        "Return only the transcribed text without quotes or commentary. "
        "If the audio is silent or empty, return an empty string."
    ),
    "zh": (
        "请将这段音频中的语音准确转写为文字。"
        "仅返回识别出的文字内容，不要包含任何多余解释或引号。"
        "如果音频仅为静音，请返回空字符串。"
    ),
}


class GeminiSTTProvider(STTProvider):
    """Transcribes audio using Gemini multimodal audio understanding."""

    name = "gemini"
    is_mock = False

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.5-flash-lite",
        timeout_ms: int = 12000,
        per_attempt_timeout_s: float = 6.0,
    ) -> None:
        self._client = create_gemini_client(api_key=api_key, timeout_ms=timeout_ms)
        self._model = model
        self._per_attempt_timeout_s = per_attempt_timeout_s

    def _build_config(self, model_name: str) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            temperature=0.0,
            thinking_config=thinking_config_for_model(model_name),
        )

    async def transcribe(
        self,
        audio_bytes: bytes,
        mime_type: str = "audio/pcm",
        sample_rate: int = 16000,
        language: str = "uz",
    ) -> STTResult:
        start = time.perf_counter()
        if not audio_bytes:
            return STTResult(text="", provider=self.name, is_mock=False, latency_ms=0.0)

        normalized_mime = (mime_type or "audio/pcm").split(";")[0].strip().lower()
        if normalized_mime in {"audio/pcm", "audio/l16"}:
            duration_ms = estimate_pcm16_duration_ms(len(audio_bytes), sample_rate=sample_rate)
            rms = compute_pcm16_rms(audio_bytes)
            if duration_ms < 120 or rms < 0.0005:
                return STTResult(
                    text="",
                    provider=self.name,
                    is_mock=False,
                    note="Sukut yoki juda qisqa audio.",
                    latency_ms=round((time.perf_counter() - start) * 1000.0, 2),
                )

        _, payload, content_type = ensure_audio_filename_and_bytes(
            audio_bytes, mime_type=mime_type, sample_rate=sample_rate
        )

        clean_lang = (language or "uz").lower().strip()
        prompt = STT_PROMPTS_BY_LANG.get(
            clean_lang,
            f"Transcribe the speech in language '{clean_lang}' accurately. Return only the transcript text."
        )

        response, used_model = await generate_with_failover(
            client=self._client,
            models=ordered_gemini_models(self._model),
            contents=[prompt, types.Part.from_bytes(data=payload, mime_type=content_type)],
            config_builder=self._build_config,
            per_attempt_timeout_s=self._per_attempt_timeout_s,
        )

        transcript = (response.text or "").strip().strip('"').strip()
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        note = (
            f"Zaxira model ({used_model})"
            if used_model != self._model
            else None
        )
        return STTResult(
            text=transcript,
            provider=self.name,
            is_mock=False,
            note=note,
            latency_ms=latency_ms,
        )
