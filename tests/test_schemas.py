from app.models.schemas import (
    HealthResponse,
    LatencyBreakdown,
    TranslateTextRequest,
    TranslateVoiceResponse,
    VoiceItem,
)


def test_translate_text_request_validation():
    req = TranslateTextRequest(text="Salom dunyo", direction="uz-ru")
    assert req.text == "Salom dunyo"
    assert req.direction == "uz-ru"
    assert req.synthesize_audio is True


def test_translate_voice_response_structure():
    resp = TranslateVoiceResponse(
        source_text="Salom",
        translated_text="Привет",
        direction="uz-ru",
        audio_base64="ZHVtbXk=",
        latency=LatencyBreakdown(stt_ms=10.0, translation_ms=20.0, tts_ms=30.0, total_ms=60.0),
    )
    assert resp.source_text == "Salom"
    assert resp.translated_text == "Привет"
    assert resp.latency.total_ms == 60.0


def test_health_response():
    hr = HealthResponse(
        status="ok",
        app_name="Ovozli Tarjimon",
        version="1.0.0",
        active_stt="gemini",
        active_translation="gemini",
        active_tts="edge_tts",
        configured_providers={"gemini": True, "openai": False, "edge_tts": True},
    )
    assert hr.status == "ok"
