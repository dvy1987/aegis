from __future__ import annotations

import logging
import os
import random
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)

DEFAULT_FALLBACK_MODEL = "gemini-3.5-flash"
DEFAULT_FALLBACK_THINKING_LEVEL = "high"

_LOCK = threading.Lock()
_LAST_CALL_AT = 0.0
_RETRYABLE_MARKERS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
    "DEADLINE_EXCEEDED",
)


def fallback_model_name() -> str:
    return os.environ.get("AEGIS_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL)


def fallback_thinking_level() -> str:
    return os.environ.get("AEGIS_FALLBACK_THINKING_LEVEL", DEFAULT_FALLBACK_THINKING_LEVEL)


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _retryable(exc: Exception) -> bool:
    message = str(exc).upper()
    return any(marker in message for marker in _RETRYABLE_MARKERS)


def pace_gemini_call() -> None:
    """Public pacing hook shared by sync clients and ADK model wrappers."""
    _pace()


def max_retries() -> int:
    return _int_env("AEGIS_GEMINI_MAX_RETRIES", 4)


def backoff_seconds(attempt: int) -> float:
    return _backoff_seconds(attempt)


def is_retryable(exc: Exception) -> bool:
    return _retryable(exc)


def _pace() -> None:
    global _LAST_CALL_AT
    min_interval = _float_env("AEGIS_GEMINI_MIN_INTERVAL_SECONDS", 2.0)
    if min_interval <= 0:
        return
    with _LOCK:
        now = time.monotonic()
        wait = max(0.0, (_LAST_CALL_AT + min_interval) - now)
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL_AT = time.monotonic()


def _backoff_seconds(attempt: int) -> float:
    base = _float_env("AEGIS_GEMINI_BACKOFF_BASE_SECONDS", 5.0)
    cap = _float_env("AEGIS_GEMINI_BACKOFF_MAX_SECONDS", 60.0)
    delay = min(cap, base * (2**attempt))
    jitter = _float_env("AEGIS_GEMINI_BACKOFF_JITTER_SECONDS", 0.5)
    return delay + random.uniform(0, max(0.0, jitter))


def generate_content_with_retry(generate_content: Callable[..., T], **kwargs) -> T:
    max_retries = _int_env("AEGIS_GEMINI_MAX_RETRIES", 4)
    for attempt in range(max_retries + 1):
        _pace()
        try:
            return generate_content(**kwargs)
        except Exception as exc:
            if attempt >= max_retries or not _retryable(exc):
                raise
            time.sleep(_backoff_seconds(attempt))
    raise RuntimeError("unreachable Gemini retry state")


def _model_unavailable(exc: Exception, model: str) -> bool:
    """True when the failure is 'this model name isn't available here' (vs a
    transient error). We only swap models in that case."""
    msg = str(exc)
    return ("404" in msg or "NOT_FOUND" in msg) and "gemini-3.1" in (model or "")


def _kwargs_for_fallback_model(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Copy kwargs and attach high-thinking config for the fallback Flash model."""
    from google.genai import types

    out = dict(kwargs)
    thinking = types.ThinkingConfig(thinking_level=fallback_thinking_level())
    config = out.get("config")
    if config is None:
        out["config"] = types.GenerateContentConfig(thinking_config=thinking)
    elif isinstance(config, types.GenerateContentConfig):
        out["config"] = config.model_copy(update={"thinking_config": thinking})
    else:
        out["config"] = types.GenerateContentConfig(thinking_config=thinking)
    return out


def generate_content_with_fallback(
    generate_content: Callable[..., T],
    *,
    model: str,
    fallback_model: str | None = None,
    **kwargs,
) -> T:
    """Retry helper that also survives a model name being unavailable.

    First tries ``model`` with the normal transient-error retry/backoff. If that
    fails specifically because the model name isn't available in this
    project/region (a 404 / NOT_FOUND on a gemini-3.1 name), it retries the SAME
    request once on the fallback model (default ``gemini-3.5-flash`` with
    ``thinking_level=high``). This is NOT a way to skip the call — it runs the
    identical task on a different available engine. Any other error propagates
    so callers can decide how to degrade.
    """
    resolved_fallback = fallback_model or fallback_model_name()
    try:
        return generate_content_with_retry(generate_content, model=model, **kwargs)
    except Exception as exc:
        if resolved_fallback and _model_unavailable(exc, model):
            logger.warning(
                "model %s unavailable; retrying on fallback %s (thinking_level=%s)",
                model,
                resolved_fallback,
                fallback_thinking_level(),
            )
            fallback_kwargs = _kwargs_for_fallback_model(kwargs)
            return generate_content_with_retry(
                generate_content, model=resolved_fallback, **fallback_kwargs
            )
        raise
