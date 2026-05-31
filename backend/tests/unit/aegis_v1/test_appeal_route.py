from fastapi import FastAPI
from starlette.testclient import TestClient

from app.aegis_v1.appeal_api import get_drafter_client, get_simulator_client, router
from app.aegis_v1.drafter_client import StubDrafterClient
from app.aegis_v1.simulator_client import StubSimulatorClient, uniform_assessment


def _client(anchor: int = 5) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_drafter_client] = lambda: StubDrafterClient()
    app.dependency_overrides[get_simulator_client] = lambda: StubSimulatorClient(
        assessment=uniform_assessment(anchor)
    )
    return TestClient(app)


def test_post_appeal_returns_letter_and_outcome_offline():
    resp = _client(anchor=5).post(
        "/v1/appeal",
        json={
            "denial_text": "Cigna denied TMS as not medically necessary.",
            "clinical_context": "Patient failed two SSRIs.",
            "case_id": "case_http",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["appeal_letter"]
    assert body["outcome"]["verdict"] == "APPROVE"
    assert body["run_id"].startswith("aegis-v1-")
    assert body["trace_metadata"]["case_id"] == "case_http"


def test_post_appeal_surfaces_a_deny_outcome():
    resp = _client(anchor=1).post(
        "/v1/appeal",
        json={"denial_text": "Denied: not medically necessary.", "case_id": "x"},
    )
    assert resp.status_code == 200
    assert resp.json()["outcome"]["verdict"] == "DENY"
