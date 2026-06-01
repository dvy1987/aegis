from __future__ import annotations

import os

from fastapi import FastAPI
from starlette.testclient import TestClient

from app.aegis_swarm.appeal_api import (
    get_simulator_client,
    get_swarm_stack,
    get_trace_recorder,
    router,
)
from app.aegis_swarm.client import StubSwarmClient
from app.aegis_swarm.corpus_store import LocalCorpusStore
from app.aegis_swarm.literature_discovery import LiteratureDiscovery
from app.aegis_swarm.trace_recorder import InMemorySwarmTraceRecorder
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment


def _client(anchor: int = 5) -> TestClient:
    os.environ["AEGIS_SWARM_TRACE_MODE"] = "memory"
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_swarm_stack] = lambda: {
        "client": StubSwarmClient(),
        "corpus_store": LocalCorpusStore(),
        "discovery": LiteratureDiscovery(),
    }
    app.dependency_overrides[get_trace_recorder] = lambda: InMemorySwarmTraceRecorder()
    app.dependency_overrides[get_simulator_client] = lambda: StubSimulatorClient(
        assessment=uniform_assessment(anchor)
    )
    return TestClient(app)


def test_swarm_appeal_route() -> None:
    resp = _client(anchor=5).post(
        "/v1/swarm/appeal",
        json={
            "denial_text": (
                "UnitedHealthcare denied the requested service as not medically necessary."
            ),
            "case_id": "api-test-1",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"].startswith("aegis-swarm-")
    assert "appeal_letter" in body
    assert body["outcome"]["verdict"] == "APPROVE"
    assert body["artifacts"]["routing_manifest"]
