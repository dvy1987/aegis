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
            "case_id": "case_http",
            "insurer": "Cigna",
            "patient_age": 42,
            "patient_gender": "F",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["appeal_letter"]
    assert body["outcome"]["verdict"] == "APPROVE"
    assert body["run_id"].startswith("aegis-v1-")
    assert body["trace_metadata"]["case_id"] == "case_http"


def test_post_appeal_includes_optional_clinical_notes_in_drafter_context():
    resp = _client(anchor=5).post(
        "/v1/appeal",
        json={
            "denial_text": "Cigna denied TMS as not medically necessary.",
            "case_id": "case_http_notes",
            "insurer": "Cigna",
            "patient_age": 42,
            "patient_gender": "F",
            "clinical_context": "Failed two SSRIs.",
        },
    )
    assert resp.status_code == 200
    parsed = resp.json()
    # Stub drafter echoes parsed case context into the letter body indirectly;
    # verify the pipeline accepted the request with notes via parsed_case in package.
    # The offline stub letter is static; we only assert the route accepts notes.
    assert parsed["appeal_letter"]


def test_post_appeal_surfaces_a_deny_outcome():
    resp = _client(anchor=1).post(
        "/v1/appeal",
        json={
            "denial_text": "Denied: not medically necessary.",
            "case_id": "x",
            "insurer": "Aetna",
            "patient_age": 30,
            "patient_gender": "M",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["outcome"]["verdict"] == "DENY"
