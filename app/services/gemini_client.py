"""Shared Google Gemini client, failover engine, and error formatting."""

import asyncio
import time
from collections.abc import Callable
from typing import Any, Optional

from google import genai
from google.genai import types

# Fastest and most reliable model first
DEFAULT_GEMINI_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
)

_MODEL_COOLDOWN_UNTIL: dict[str, float] = {}


def clear_model_cooldowns() -> None:
    _MODEL_COOLDOWN_UNTIL.clear()


def _mark_cooldown(model_name: str, exc: Exception) -> None:
    msg = str(exc).upper()
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "QUOTA" in msg:
        _MODEL_COOLDOWN_UNTIL[model_name] = time.monotonic() + 180.0
    elif "404" in msg or "NOT_FOUND" in msg:
        _MODEL_COOLDOWN_UNTIL[model_name] = time.monotonic() + 3600.0
    elif isinstance(exc, TimeoutError) or "TIMEOUT" in msg or "503" in msg or "UNAVAILABLE" in msg:
        _MODEL_COOLDOWN_UNTIL[model_name] = time.monotonic() + 30.0
    else:
        _MODEL_COOLDOWN_UNTIL[model_name] = time.monotonic() + 20.0


def thinking_config_for_model(model_name: str) -> Optional[types.ThinkingConfig]:
    lower = model_name.lower()
    if "lite" in lower:
        return None
    return types.ThinkingConfig(thinking_budget=0)


def format_user_friendly_error(exc: Exception) -> str:
    raw = str(exc)
    upper = raw.upper()
    if "429" in upper or "RESOURCE_EXHAUSTED" in upper or "QUOTA" in upper:
        return (
            "AI so'rov limiti tugadi (429). "
            "Biroz kuting yoki tizim zaxira modeliga o'tadi."
        )
    if "401" in upper or "403" in upper or "API_KEY_INVALID" in upper:
        return "API kaliti noto'g'ri yoki ruxsati cheklangan."
    if isinstance(exc, TimeoutError) or "TIMEOUT" in upper:
        return "AI serveridan javob kutish vaqti tugadi. Qayta urinib ko'ring."
    if "503" in upper or "UNAVAILABLE" in upper:
        return "AI serveri hozir band (503). Bir ozdan keyin qayta urinib ko'ring."
    clean = raw.splitlines()[0].strip()
    return clean[:160] + ("..." if len(clean) > 160 else "")


def create_gemini_client(api_key: str, timeout_ms: int = 12000) -> genai.Client:
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=max(12000, timeout_ms),
        ),
    )


def ordered_gemini_models(primary_model: Optional[str] = None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    candidates = ([primary_model] if primary_model else []) + list(DEFAULT_GEMINI_MODELS)
    for model in candidates:
        if not model:
            continue
        clean = model.strip()
        if clean and clean not in seen:
            seen.add(clean)
            ordered.append(clean)
    return ordered


async def generate_with_failover(
    client: genai.Client,
    models: list[str],
    contents: Any,
    config_builder: Optional[Callable[[str], types.GenerateContentConfig]] = None,
    per_attempt_timeout_s: float = 6.0,
    total_budget_s: float = 12.0,
) -> tuple[types.GenerateContentResponse, str]:
    now = time.monotonic()
    deadline = now + total_budget_s

    available_models = [
        m for m in models if _MODEL_COOLDOWN_UNTIL.get(m, 0.0) <= now
    ]
    if not available_models:
        _MODEL_COOLDOWN_UNTIL.clear()
        available_models = models

    last_error: Optional[Exception] = None

    for model in available_models:
        remaining = deadline - time.monotonic()
        if remaining <= 0.4:
            break

        attempt_timeout = min(per_attempt_timeout_s, remaining)
        config = config_builder(model) if config_builder else None

        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                ),
                timeout=attempt_timeout,
            )
            return response, model
        except Exception as exc:
            last_error = exc
            _mark_cooldown(model, exc)
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Gemini modellariga ulanib bo'lmadi (vaqt tugadi).")
