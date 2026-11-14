import pytest
from app.services.tts.edge_tts_service import EdgeTTSProvider
from app.services.tts.mock_tts import MockTTSProvider


@pytest.mark.asyncio
async def test_mock_tts_provider():
    mock_tts = MockTTSProvider()
    res = await mock_tts.synthesize("Привет, это тестовый голос.")
    assert res.audio_bytes.startswith(b"RIFF")
    assert res.mime_type == "audio/wav"
    assert res.latency_ms >= 0


@pytest.mark.asyncio
async def test_edge_tts_empty():
    tts = EdgeTTSProvider()
    res = await tts.synthesize("   ")
    assert res.audio_bytes == b""
