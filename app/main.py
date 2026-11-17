"""FastAPI web and WebSocket application for Ovozli Tarjimon."""

import asyncio
import base64
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.models.schemas import (
    HealthResponse,
    LanguageItem,
    TranslateTextRequest,
    TranslateVoiceResponse,
    VoiceItem,
)
from app.pipeline import VoiceTranslatorPipeline
from app.services.gemini_client import format_user_friendly_error
from app.services.tts.edge_tts_service import AVAILABLE_VOICES

STATIC_DIR = Path(__file__).resolve().parent / "static"

SUPPORTED_LANGUAGES: list[LanguageItem] = [
    LanguageItem(code="uz", name="O'zbekcha", flag="🇺🇿", default_voice="uz-UZ-MadinaNeural"),
    LanguageItem(code="ru", name="Русский", flag="🇷🇺", default_voice="ru-RU-SvetlanaNeural"),
    LanguageItem(code="tr", name="Türkçe", flag="🇹🇷", default_voice="tr-TR-EmelNeural"),
    LanguageItem(code="en", name="English", flag="🇬🇧", default_voice="en-US-AvaNeural"),
    LanguageItem(code="zh", name="中文 (Chinese)", flag="🇨🇳", default_voice="zh-CN-XiaoxiaoNeural"),
]


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    cfg = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield

    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        description="Ko'p tilli AI Ovozli Tarjimon (O'zbek, Rus, Turk, Ingliz, Xitoy)",
        lifespan=lifespan,
    )

    origins = cfg.cors_origin_list()
    if "*" in origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.state.settings = cfg
    app.state.pipeline = VoiceTranslatorPipeline(cfg)

    def get_pipeline() -> VoiceTranslatorPipeline:
        return app.state.pipeline

    def get_cfg() -> Settings:
        return app.state.settings

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def index_page() -> Any:
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Ovozli Tarjimon API faol", "docs": "/docs"}

    @app.get("/health", response_model=HealthResponse)
    async def health(active_cfg: Settings = Depends(get_cfg)) -> HealthResponse:
        return HealthResponse(
            status="ok",
            app_name=active_cfg.app_name,
            version=active_cfg.app_version,
            active_stt=active_cfg.resolved_stt_provider(),
            active_translation=active_cfg.resolved_translation_provider(),
            active_tts=active_cfg.resolved_tts_provider(),
            configured_providers={
                "gemini": bool(active_cfg.gemini_api_key),
                "openai": bool(active_cfg.openai_api_key),
                "edge_tts": True,
            },
            supported_languages=[l.code for l in SUPPORTED_LANGUAGES],
        )

    @app.get("/api/v1/languages", response_model=list[LanguageItem])
    async def list_languages() -> list[LanguageItem]:
        """Return supported languages with codes, names, flags and default voices."""
        return SUPPORTED_LANGUAGES

    @app.get("/api/v1/voices", response_model=list[VoiceItem])
    async def list_voices() -> list[VoiceItem]:
        """Return available neural voices for speech synthesis across languages."""
        return AVAILABLE_VOICES

    @app.post("/api/v1/translate-text", response_model=TranslateVoiceResponse)
    async def translate_text(
        body: TranslateTextRequest,
        pipeline: VoiceTranslatorPipeline = Depends(get_pipeline),
    ) -> TranslateVoiceResponse:
        """Translate text across languages and synthesize speech."""
        src, tgt = body.resolve_languages()
        try:
            return await pipeline.process_text(
                text=body.text,
                source_lang=src,
                target_lang=tgt,
                voice=body.voice,
                rate=body.rate or "+0%",
                synthesize_audio=body.synthesize_audio,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=format_user_friendly_error(exc)
            ) from exc

    @app.post("/api/v1/translate-audio", response_model=TranslateVoiceResponse)
    async def translate_audio(
        file: UploadFile = File(...),
        source_lang: Optional[str] = Form(default=None),
        target_lang: Optional[str] = Form(default=None),
        direction: Optional[str] = Form(default=None),
        voice: Optional[str] = Form(default=None),
        rate: str = Form(default="+0%"),
        sample_rate: int = Form(default=16000),
        pipeline: VoiceTranslatorPipeline = Depends(get_pipeline),
        active_cfg: Settings = Depends(get_cfg),
    ) -> TranslateVoiceResponse:
        """Upload voice audio (WAV, MP3, WebM, OGG), translate and synthesize speech."""
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Audio fayl bo'sh.")
        if len(audio_bytes) > active_cfg.max_audio_bytes:
            raise HTTPException(status_code=413, detail="Audio hajmi ruxsat etilgan limitdan katta.")

        mime_type = file.content_type or "audio/wav"
        try:
            return await pipeline.process_audio(
                audio_bytes=audio_bytes,
                mime_type=mime_type,
                sample_rate=sample_rate,
                source_lang=source_lang,
                target_lang=target_lang,
                direction=direction,
                voice=voice,
                rate=rate,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=format_user_friendly_error(exc)
            ) from exc

    @app.get("/api/v1/tts")
    async def tts_endpoint(
        text: str,
        voice: str = "ru-RU-SvetlanaNeural",
        rate: str = "+0%",
        pipeline: VoiceTranslatorPipeline = Depends(get_pipeline),
    ) -> Response:
        """Direct text-to-speech endpoint returning audio/mpeg stream."""
        if not text.strip():
            raise HTTPException(status_code=400, detail="Matn bo'sh bo'lishi mumkin emas.")
        res = await pipeline.tts_provider.synthesize(text=text, voice=voice, rate=rate)
        return Response(content=res.audio_bytes, media_type=res.mime_type)

    @app.websocket("/ws/translator")
    async def translator_websocket(websocket: WebSocket) -> None:
        """Real-time streaming WebSocket endpoint with progressive stage updates."""
        await websocket.accept()
        pipeline: VoiceTranslatorPipeline = app.state.pipeline
        active_cfg: Settings = app.state.settings

        audio_buffer = bytearray()
        source_lang = "uz"
        target_lang = "ru"
        voice: Optional[str] = None
        rate = "+0%"
        mime_type = "audio/pcm"
        sample_rate = 16000

        await websocket.send_json(
            {
                "type": "connected",
                "message": "Ovozli Tarjimon serveriga ulandingiz",
                "default_source_lang": source_lang,
                "default_target_lang": target_lang,
                "languages": [l.model_dump() for l in SUPPORTED_LANGUAGES],
            }
        )

        try:
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break

                raw_bytes = message.get("bytes")
                if raw_bytes is not None:
                    if len(audio_buffer) + len(raw_bytes) > active_cfg.max_audio_bytes:
                        audio_buffer.clear()
                        await websocket.send_json(
                            {"type": "error", "message": "Audio hajmi oshib ketdi."}
                        )
                        continue
                    audio_buffer.extend(raw_bytes)
                    continue

                raw_text = message.get("text")
                if raw_text is None:
                    continue

                try:
                    data = json.loads(raw_text)
                except Exception:
                    await websocket.send_json({"type": "error", "message": "Noto'g'ri JSON."})
                    continue

                msg_type = data.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "start_utterance":
                    audio_buffer.clear()
                    source_lang = data.get("source_lang", source_lang)
                    target_lang = data.get("target_lang", target_lang)
                    if "direction" in data and "-" in data["direction"]:
                        parts = data["direction"].split("-", 1)
                        source_lang, target_lang = parts[0], parts[1]
                    voice = data.get("voice") or voice
                    rate = data.get("rate", rate)
                    mime_type = data.get("mime_type", "audio/pcm")
                    sample_rate = int(data.get("sample_rate", 16000))
                    await websocket.send_json({"type": "utterance_started"})

                elif msg_type == "audio_chunk":
                    chunk_b64 = data.get("data", "")
                    if chunk_b64:
                        decoded = base64.b64decode(chunk_b64)
                        if len(audio_buffer) + len(decoded) <= active_cfg.max_audio_bytes:
                            audio_buffer.extend(decoded)

                elif msg_type == "end_utterance":
                    source_lang = data.get("source_lang", source_lang)
                    target_lang = data.get("target_lang", target_lang)
                    if "direction" in data and "-" in data["direction"]:
                        parts = data["direction"].split("-", 1)
                        source_lang, target_lang = parts[0], parts[1]
                    voice = data.get("voice") or voice
                    rate = data.get("rate", rate)

                    payload = bytes(audio_buffer)
                    audio_buffer.clear()

                    if not payload:
                        await websocket.send_json(
                            {"type": "error", "message": "Audio yuborilmadi."}
                        )
                        continue

                    # Progressive stage notifier callback
                    async def stage_callback(stage_name: str, stage_data: Any):
                        try:
                            if stage_name == "stt_started":
                                await websocket.send_json({"type": "stage", "stage": "Transkripsiya..."})
                            elif stage_name == "transcript_ready":
                                await websocket.send_json({"type": "transcript", "source_text": stage_data})
                            elif stage_name == "translation_started":
                                await websocket.send_json({"type": "stage", "stage": "Tarjima qilinmoqda..."})
                            elif stage_name == "translation_ready":
                                await websocket.send_json({"type": "translation", "translated_text": stage_data})
                            elif stage_name == "tts_started":
                                await websocket.send_json({"type": "stage", "stage": "Ovozlashtirilmoqda..."})
                        except Exception:
                            pass

                    try:
                        result = await pipeline.process_audio(
                            audio_bytes=payload,
                            mime_type=mime_type,
                            sample_rate=sample_rate,
                            source_lang=source_lang,
                            target_lang=target_lang,
                            voice=voice,
                            rate=rate,
                            on_stage_callback=stage_callback,
                        )
                        await websocket.send_json(
                            {"type": "result", "payload": result.model_dump()}
                        )
                    except Exception as exc:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": format_user_friendly_error(exc),
                            }
                        )

        except WebSocketDisconnect:
            pass
        except Exception as exc:
            try:
                await websocket.send_json({"type": "error", "message": str(exc)})
            except Exception:
                pass

    return app


app = create_app()
