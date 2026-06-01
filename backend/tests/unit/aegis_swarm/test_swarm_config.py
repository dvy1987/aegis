from __future__ import annotations

from app.aegis_swarm.client import GeminiSwarmClient, StubSwarmClient
from app.aegis_swarm.literature_discovery import FakeDiscoverySearchClient
from app.aegis_swarm.swarm_config import build_live_stack, build_swarm_client, swarm_mode


def test_swarm_mode_defaults_stub(monkeypatch) -> None:
    monkeypatch.delenv("AEGIS_SWARM_MODE", raising=False)
    assert swarm_mode() == "stub"
    assert isinstance(build_swarm_client(), StubSwarmClient)


def test_live_mode_builds_gemini_client(monkeypatch) -> None:
    monkeypatch.setenv("AEGIS_SWARM_MODE", "live")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    client = build_swarm_client()
    assert isinstance(client, GeminiSwarmClient)
    assert client.location == "us-central1"


def test_live_stack_wires_offline_defaults(monkeypatch) -> None:
    monkeypatch.delenv("AEGIS_SWARM_MODE", raising=False)
    monkeypatch.delenv("VERTEX_SEARCH_DATA_STORE_ID", raising=False)
    stack = build_live_stack()
    assert isinstance(stack["client"], StubSwarmClient)
    assert isinstance(stack["discovery"].search_client, FakeDiscoverySearchClient)
