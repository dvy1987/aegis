from __future__ import annotations

import contextvars
from typing import Any

_controlled_retrieval: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "aegis_v1_controlled_retrieval", default=None
)


def set_controlled_retrieval(retrieval: dict[str, Any]):
    return _controlled_retrieval.set(retrieval)


def reset_controlled_retrieval(token: contextvars.Token) -> None:
    _controlled_retrieval.reset(token)


def get_controlled_retrieval() -> dict[str, Any] | None:
    return _controlled_retrieval.get()
