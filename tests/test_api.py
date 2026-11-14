import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    cfg = Settings(
        stt_provider="mock",
        translation_provider="mock",
        tts_provider="mock",
        gemini_api_key="",
    )
    app = create_app(cfg)
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "supported_languages" in data
    assert "tr" in data["supported_languages"]


def test_languages_endpoint(client):
    response = client.get("/api/v1/languages")
    assert response.status_code == 200
    langs = response.json()
    codes = [l["code"] for l in langs]
    assert "uz" in codes
    assert "ru" in codes
    assert "tr" in codes
    assert "en" in codes
    assert "zh" in codes


def test_voices_endpoint(client):
    response = client.get("/api/v1/voices")
    assert response.status_code == 200
    voices = response.json()
    assert len(voices) >= 8
    ids = [v["id"] for v in voices]
    assert "ru-RU-SvetlanaNeural" in ids
    assert "tr-TR-EmelNeural" in ids
    assert "zh-CN-XiaoxiaoNeural" in ids
    assert "en-US-AvaNeural" in ids
    assert "uz-UZ-MadinaNeural" in ids


def test_translate_text_endpoint_uz_to_tr(client):
    response = client.post(
        "/api/v1/translate-text",
        json={"text": "Salom", "source_lang": "uz", "target_lang": "tr", "synthesize_audio": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_text"] == "Salom"
    assert data["translated_text"] == "merhaba"
    assert data["source_lang"] == "uz"
    assert data["target_lang"] == "tr"


def test_translate_text_endpoint_tr_to_uz(client):
    response = client.post(
        "/api/v1/translate-text",
        json={"text": "Teşekkür ederim", "source_lang": "tr", "target_lang": "uz", "synthesize_audio": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["translated_text"] == "rahmat"


def test_tts_endpoint(client):
    response = client.get("/api/v1/tts", params={"text": "Merhaba", "voice": "tr-TR-EmelNeural"})
    assert response.status_code == 200
    assert len(response.content) > 0


def test_root_serves_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Ovozli Tarjimon" in response.text
    assert "tr-TR-EmelNeural" in response.text
    assert "srcPills" in response.text
    assert "tgtPills" in response.text
