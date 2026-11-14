"""Multi-language Translation Service supporting Uzbek, Russian, English, Chinese, Turkish."""

import time
from typing import Optional
from google.genai import types
from openai import AsyncOpenAI

from app.config import Settings
from app.services.gemini_client import (
    create_gemini_client,
    generate_with_failover,
    ordered_gemini_models,
    thinking_config_for_model,
)

LANG_LABELS: dict[str, str] = {
    "uz": "o'zbek (lotin)",
    "ru": "rus (Russian)",
    "en": "ingliz (English)",
    "zh": "xitoy (Chinese Mandarin)",
    "tr": "turk (Türkçe)",
}

# In-memory translation cache: (text_clean, source_lang, target_lang) -> translated_text
_TRANSLATION_CACHE: dict[tuple[str, str, str], str] = {}


def build_system_instruction(source_lang: str, target_lang: str) -> str:
    src_label = LANG_LABELS.get(source_lang, source_lang)
    tgt_label = LANG_LABELS.get(target_lang, target_lang)
    return (
        f"Siz professional ko'p tilli sinxron tarjimonsiz. "
        f"Berilgan matnni {tgt_label} tiliga tabiiy, grammatik to'g'ri va ravon tarjima qiling. "
        f"(Asl matn {src_label} tilida yoki boshqa tilda bo'lishi mumkin, uni to'g'ri tushunib "
        f"aynan {tgt_label} tiliga tarjima qiling). "
        "Qoida: Faqat tayyor tarjima matnini qaytaring. Qo'shimcha so'z, izoh yoki qo'shtirnoqsiz."
    )


class TranslationResult:
    __slots__ = ("source_text", "translated_text", "source_lang", "target_lang", "direction", "provider", "latency_ms", "note")

    def __init__(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str = "uz",
        target_lang: str = "ru",
        direction: str = "uz-ru",
        provider: str = "gemini",
        latency_ms: float = 0.0,
        note: Optional[str] = None,
    ) -> None:
        self.source_text = source_text
        self.translated_text = translated_text
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.direction = direction
        self.provider = provider
        self.latency_ms = latency_ms
        self.note = note


class TranslationService:
    """Translates text between Uzbek, Russian, English, Chinese, and Turkish."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._gemini_client = None

    def _get_gemini_client(self):
        if self._gemini_client is None and self._settings.gemini_api_key:
            self._gemini_client = create_gemini_client(
                api_key=self._settings.gemini_api_key,
                timeout_ms=int(self._settings.timeout_seconds * 1000),
            )
        return self._gemini_client

    async def translate(
        self,
        text: str,
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None,
        direction: Optional[str] = None,
        provider_override: Optional[str] = None,
    ) -> TranslationResult:
        clean = text.strip()

        if source_lang and target_lang:
            src = source_lang.lower().strip()
            tgt = target_lang.lower().strip()
        elif direction and "-" in direction:
            parts = direction.lower().strip().split("-", 1)
            src, tgt = parts[0], parts[1]
        else:
            src, tgt = "uz", "ru"

        dir_str = f"{src}-{tgt}"

        if not clean:
            return TranslationResult(
                source_text="",
                translated_text="",
                source_lang=src,
                target_lang=tgt,
                direction=dir_str,
                provider="none",
                latency_ms=0.0,
            )

        if src == tgt:
            return TranslationResult(
                source_text=clean,
                translated_text=clean,
                source_lang=src,
                target_lang=tgt,
                direction=dir_str,
                provider="identity",
                latency_ms=0.0,
            )

        # 1. Check in-memory cache for 0ms instantaneous result
        cache_key = (clean, src, tgt)
        if cache_key in _TRANSLATION_CACHE:
            return TranslationResult(
                source_text=clean,
                translated_text=_TRANSLATION_CACHE[cache_key],
                source_lang=src,
                target_lang=tgt,
                direction=dir_str,
                provider="cache",
                latency_ms=0.5,
                note="Keshdan olindi",
            )

        choice = (provider_override or self._settings.resolved_translation_provider()).strip().lower()

        if choice == "gemini" and self._settings.gemini_api_key:
            res = await self._translate_with_gemini(clean, src, tgt, dir_str)
            if res.translated_text:
                _TRANSLATION_CACHE[cache_key] = res.translated_text
            return res

        if choice == "openai" and self._settings.openai_api_key:
            res = await self._translate_with_openai(clean, src, tgt, dir_str)
            if res.translated_text:
                _TRANSLATION_CACHE[cache_key] = res.translated_text
            return res

        return self._translate_mock(clean, src, tgt, dir_str)

    async def _translate_with_gemini(
        self, text: str, source_lang: str, target_lang: str, direction: str
    ) -> TranslationResult:
        start = time.perf_counter()
        client = self._get_gemini_client()
        system_prompt = build_system_instruction(source_lang, target_lang)

        def build_cfg(model_name: str) -> types.GenerateContentConfig:
            return types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0,
                max_output_tokens=150,
                thinking_config=thinking_config_for_model(model_name),
            )

        response, used_model = await generate_with_failover(
            client=client,
            models=ordered_gemini_models(self._settings.gemini_model),
            contents=text,
            config_builder=build_cfg,
            per_attempt_timeout_s=6.0,
            total_budget_s=12.0,
        )

        translated = (response.text or "").strip().strip('"').strip()
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        note = (
            f"Zaxira model ({used_model})"
            if used_model != self._settings.gemini_model
            else None
        )
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source_lang,
            target_lang=target_lang,
            direction=direction,
            provider="gemini",
            latency_ms=latency_ms,
            note=note,
        )

    async def _translate_with_openai(
        self, text: str, source_lang: str, target_lang: str, direction: str
    ) -> TranslationResult:
        start = time.perf_counter()
        client = AsyncOpenAI(
            api_key=self._settings.openai_api_key,
            timeout=self._settings.timeout_seconds,
        )
        system_prompt = build_system_instruction(source_lang, target_lang)
        completion = await client.chat.completions.create(
            model=self._settings.openai_model,
            temperature=0.0,
            max_tokens=150,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        translated = (completion.choices[0].message.content or "").strip().strip('"').strip()
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source_lang,
            target_lang=target_lang,
            direction=direction,
            provider="openai",
            latency_ms=latency_ms,
        )

    def _translate_mock(
        self, text: str, source_lang: str, target_lang: str, direction: str
    ) -> TranslationResult:
        start = time.perf_counter()
        dictionary = {
            ("uz", "ru"): {"salom": "привет", "rahmat": "спасибо", "assalomu alaykum": "здравствуйте"},
            ("ru", "uz"): {"привет": "salom", "спасибо": "rahmat", "здравствуйте": "assalomu alaykum"},
            ("uz", "en"): {"salom": "hello", "rahmat": "thank you", "assalomu alaykum": "hello"},
            ("en", "uz"): {"hello": "salom", "thank you": "rahmat", "hi": "salom"},
            ("uz", "zh"): {"salom": "你好", "rahmat": "谢谢"},
            ("zh", "uz"): {"你好": "salom", "谢谢": "rahmat"},
            ("uz", "tr"): {"salom": "merhaba", "rahmat": "teşekkür ederim", "assalomu alaykum": "selamün aleyküm"},
            ("tr", "uz"): {"merhaba": "salom", "teşekkür ederim": "rahmat", "selamün aleyküm": "assalomu alaykum"},
            ("tr", "ru"): {"merhaba": "привет", "teşekkür ederim": "спасибо"},
            ("ru", "tr"): {"привет": "merhaba", "спасибо": "teşekkür ederim"},
        }
        pair = (source_lang, target_lang)
        lookup = dictionary.get(pair, {})
        low = text.lower().strip(" .,!?")
        translated = lookup.get(low, f"[{target_lang.upper()}]: {text}")

        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        return TranslationResult(
            source_text=text,
            translated_text=translated,
            source_lang=source_lang,
            target_lang=target_lang,
            direction=direction,
            provider="mock",
            latency_ms=latency_ms,
            note="Mock tarjima rejimi",
        )
