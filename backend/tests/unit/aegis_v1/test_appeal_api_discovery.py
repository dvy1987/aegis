from __future__ import annotations

from app.aegis_v1.appeal_api import AppealRequest
from app.aegis_v1.v1_config import build_v1_library_stack


def test_appeal_request_discovery_defaults_off() -> None:
    req = AppealRequest(denial_text="Denied.")
    assert req.discovery_enabled is False


def test_library_stack_honors_request_discovery_flag() -> None:
    off = build_v1_library_stack(discovery_enabled=False)
    on = build_v1_library_stack(discovery_enabled=True)
    assert off["discovery"].config.enabled is False
    assert on["discovery"].config.enabled is True
