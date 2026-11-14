import pytest
from app.config import Settings
from app.pipeline import VoiceTranslatorPipeline


@pytest.mark.asyncio
async def test_pipeline_process_text():
    cfg = Settings(
        stt_provider="mock",
        translation_provider="mock",
        tts_provider="mock",
        gemini_api_key="",
    )
    pipeline = VoiceTranslatorPipeline(cfg)

    resp = await pipeline.process_text("Salom", direction="uz-ru")
    assert resp.source_text == "Salom"
    assert "привет" in resp.translated_text.lower()
    assert resp.audio_base64 is not None
    assert resp.latency.total_ms > 0


@pytest.mark.asyncio
async def test_pipeline_process_audio_silence():
    cfg = Settings(
        stt_provider="mock",
        translation_provider="mock",
        tts_provider="mock",
        gemini_api_key="",
    )
    pipeline = VoiceTranslatorPipeline(cfg)

    # 100ms of silence
    silence = b"\x00\x00" * 800
    resp = await pipeline.process_audio(silence, mime_type="audio/pcm", sample_rate=16000)
    assert resp.source_text == ""
    assert resp.translated_text == ""
