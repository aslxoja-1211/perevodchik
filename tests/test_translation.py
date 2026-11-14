import pytest
from app.config import Settings
from app.services.translation.translator import TranslationService


@pytest.mark.asyncio
async def test_translation_service_mock_uz_ru():
    cfg = Settings(translation_provider="mock", gemini_api_key="")
    svc = TranslationService(cfg)

    res = await svc.translate("Assalomu alaykum", source_lang="uz", target_lang="ru")
    assert "здравствуйте" in res.translated_text.lower()
    assert res.provider == "mock"
    assert res.source_lang == "uz"
    assert res.target_lang == "ru"


@pytest.mark.asyncio
async def test_translation_service_mock_uz_zh():
    cfg = Settings(translation_provider="mock", gemini_api_key="")
    svc = TranslationService(cfg)

    res = await svc.translate("Salom", source_lang="uz", target_lang="zh")
    assert res.translated_text == "你好"
    assert res.source_lang == "uz"
    assert res.target_lang == "zh"


@pytest.mark.asyncio
async def test_translation_service_same_lang():
    cfg = Settings(translation_provider="mock", gemini_api_key="")
    svc = TranslationService(cfg)

    res = await svc.translate("Hello world", source_lang="en", target_lang="en")
    assert res.translated_text == "Hello world"
    assert res.provider == "identity"


@pytest.mark.asyncio
async def test_translation_service_empty():
    cfg = Settings(translation_provider="mock")
    svc = TranslationService(cfg)

    res = await svc.translate("   ", source_lang="uz", target_lang="ru")
    assert res.translated_text == ""
    assert res.source_text == ""
