from __future__ import annotations

import os
import random
import threading
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

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
