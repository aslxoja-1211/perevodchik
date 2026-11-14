"""Microsoft Edge TTS neural speech synthesis provider with in-memory audio caching."""

import time
from typing import Optional
import edge_tts

from app.models.schemas import VoiceItem
from app.services.tts.base import TTSProvider, TTSResult

# In-memory audio cache: (clean_text, voice, rate) -> audio_bytes
_TTS_CACHE: dict[tuple[str, str, str], bytes] = {}

AVAILABLE_VOICES: list[VoiceItem] = [
    # 🇷🇺 Russian Voices
    VoiceItem(
        id="ru-RU-SvetlanaNeural",
        name="Светлана (Svetlana)",
        gender="Female",
        language="ru",
        description="Tabiiy va ravon ruscha ayol ovozi (Tavsiya etiladi)",
    ),
    VoiceItem(
        id="ru-RU-DmitryNeural",
        name="Дмитрий (Dmitry)",
        gender="Male",
        language="ru",
        description="Vazmin va aniq ruscha erkak ovozi",
    ),
    VoiceItem(
        id="ru-RU-EkaterinaNeural",
        name="Екатерина (Ekaterina)",
        gender="Female",
        language="ru",
        description="Rasmiy ruscha ayol ovozi",
    ),
    # 🇹🇷 Turkish Voices
    VoiceItem(
        id="tr-TR-EmelNeural",
        name="Emel (Türkçe)",
        gender="Female",
        language="tr",
        description="Doğal ve akıcı Türkçe kadın sesi (Tavsiye edilir)",
    ),
    VoiceItem(
        id="tr-TR-AhmetNeural",
        name="Ahmet (Türkçe)",
        gender="Male",
        language="tr",
        description="Net ve kendinden emin Türkçe erkek sesi",
    ),
    # 🇺🇿 Uzbek Voices
    VoiceItem(
        id="uz-UZ-MadinaNeural",
        name="Madina (O'zbekcha)",
        gender="Female",
        language="uz",
        description="Yoqimli o'zbekcha ayol ovozi (Tavsiya etiladi)",
    ),
    VoiceItem(
        id="uz-UZ-SardorNeural",
        name="Sardor (O'zbekcha)",
        gender="Male",
        language="uz",
        description="Aniq o'zbekcha erkak ovozi",
    ),
    # 🇬🇧/🇺🇸 English Voices
    VoiceItem(
        id="en-US-AvaNeural",
        name="Ava (US)",
        gender="Female",
        language="en",
        description="Natural and fluent English female voice",
    ),
    VoiceItem(
        id="en-US-AndrewNeural",
        name="Andrew (US)",
        gender="Male",
        language="en",
        description="Warm and confident English male voice",
    ),
    # 🇨🇳 Chinese Voices
    VoiceItem(
        id="zh-CN-XiaoxiaoNeural",
        name="晓晓 (Xiaoxiao)",
        gender="Female",
        language="zh",
        description="温暖自然的中文普通话女声 (推荐)",
    ),
    VoiceItem(
        id="zh-CN-YunxiNeural",
        name="云希 (Yunxi)",
        gender="Male",
        language="zh",
        description="沉稳生动的中文普通话男声",
    ),
]

DEFAULT_VOICES_BY_LANG: dict[str, str] = {
    "ru": "ru-RU-SvetlanaNeural",
    "tr": "tr-TR-EmelNeural",
    "uz": "uz-UZ-MadinaNeural",
    "en": "en-US-AvaNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
}


class EdgeTTSProvider(TTSProvider):
    """High-quality zero-cost Microsoft Edge Neural TTS provider with caching."""

    name = "edge_tts"
    is_mock = False

    def __init__(self, default_voice: str = "ru-RU-SvetlanaNeural") -> None:
        self.default_voice = default_voice

    def resolve_voice_for_lang(self, target_lang: str, requested_voice: Optional[str] = None) -> str:
        if requested_voice:
            return requested_voice
        clean_lang = (target_lang or "ru").lower().strip()
        return DEFAULT_VOICES_BY_LANG.get(clean_lang, self.default_voice)

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> TTSResult:
        start = time.perf_counter()
        clean_text = text.strip()
        selected_voice = voice or self.default_voice
        eff_rate = rate or "+0%"

        if not clean_text:
            return TTSResult(
                audio_bytes=b"",
                mime_type="audio/mpeg",
                voice=selected_voice,
                latency_ms=0.0,
            )

        # Check in-memory audio cache
        cache_key = (clean_text, selected_voice, eff_rate)
        if cache_key in _TTS_CACHE:
            return TTSResult(
                audio_bytes=_TTS_CACHE[cache_key],
                mime_type="audio/mpeg",
                voice=selected_voice,
                latency_ms=0.5,
                note="Keshdan olindi",
            )

        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=selected_voice,
            rate=eff_rate,
            pitch=pitch or "+0Hz",
        )

        audio_chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        audio_bytes = b"".join(audio_chunks)
        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)

        if audio_bytes:
            _TTS_CACHE[cache_key] = audio_bytes

        return TTSResult(
            audio_bytes=audio_bytes,
            mime_type="audio/mpeg",
            voice=selected_voice,
            latency_ms=latency_ms,
        )
