from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_controlled_retrieval_context() -> None:
    """Prevent pipeline contextvars from leaking across tests in one worker."""
    from app.aegis_v1.retrieval_context import _controlled_retrieval

    token = _controlled_retrieval.set(None)
    yield
    _controlled_retrieval.reset(token)
