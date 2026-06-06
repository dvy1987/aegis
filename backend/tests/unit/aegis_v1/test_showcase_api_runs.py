from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.aegis_v1.showcase_api import router


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AEGIS_SHOWCASE_LEDGER_DIR", str(tmp_path))
    monkeypatch.setenv("AEGIS_SHOWCASE_AUTORUN", "false")
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_manifest_endpoint_returns_quick_slice(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    res = client.get("/v1/showcase/manifest")

    assert res.status_code == 200
    body = res.json()
    assert body["benchmark_id"] == "v1_showcase_100"
    assert body["quick_slice"] == "Cigna:medical_necessity"
    assert len(body["quick_train"]) == 8
    assert len(body["quick_holdout"]) == 2
    assert body["serious_train_count"] == 80
    assert len(body["serious_holdout"]) == 20


def test_quick_run_start_returns_pollable_session(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    start = client.post("/v1/showcase/runs/quick")

    assert start.status_code == 200
    session_id = start.json()["session_id"]
    assert session_id.startswith("quick_")
    assert len(start.json()["case_ids"]) == 10

    poll = client.get(f"/v1/showcase/runs/{session_id}")
    assert poll.status_code == 200
    assert poll.json()["diagnostics"]["cloud_log_filter"]


def test_serious_run_locked_until_quick_success(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    res = client.post("/v1/showcase/runs/serious")

    assert res.status_code == 409


def test_serious_run_starts_after_successful_quick(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    quick_id = client.post("/v1/showcase/runs/quick").json()["session_id"]
    from app.aegis_v1.showcase_session import ShowcaseSessionManager

    ShowcaseSessionManager(ledger_dir=tmp_path).mark_success(quick_id)

    res = client.post("/v1/showcase/runs/serious")

    assert res.status_code == 200
    assert res.json()["session_id"].startswith("serious_")
    assert len(res.json()["case_ids"]) == 100


def test_cancel_run_persists_cancel_state(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    session_id = client.post("/v1/showcase/runs/quick").json()["session_id"]

    res = client.post(f"/v1/showcase/runs/{session_id}/cancel")

    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


def test_approve_without_proposal_is_rejected(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    session_id = client.post("/v1/showcase/runs/quick").json()["session_id"]

    res = client.post(f"/v1/showcase/runs/{session_id}/approve", json={"approver": "pm"})

    assert res.status_code == 409


def test_reject_without_proposal_is_rejected(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    session_id = client.post("/v1/showcase/runs/quick").json()["session_id"]

    res = client.post(f"/v1/showcase/runs/{session_id}/reject", json={"reviewer": "pm"})

    assert res.status_code == 409
