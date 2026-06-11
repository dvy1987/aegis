from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.aegis_v1.showcase_api import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_measure_case_baseline_uses_day_zero_and_disables_phoenix(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return type(
            "R",
            (),
            {
                "appeal_package": {
                    "appeal_package_draft": {"appeal_letter": "Dear insurer,"},
                    "trace_metadata": {"prompt_version": "drafter_v1"},
                    "risk_flags": [],
                },
                "outcome": {
                    "verdict": "DENY",
                    "score": 0.55,
                    "threshold": 0.7,
                    "feature_scores": [],
                    "gaps": [],
                    "critique": "",
                    "rationale": [],
                },
            },
        )()

    monkeypatch.setattr("app.aegis_v1.appeal_orchestrator.run_appeal_with_outcome", fake_run)

    client = _client()
    res = client.post(
        "/v1/showcase/measure-case",
        json={
            "case_id": "case_168_aetna_priorauth",
            "denial_letter_text": "Denied.",
            "clinical_context": "Notes.",
            "insurer": "Aetna",
            "denial_type": "Prior authorization",
            "patient_age": 53,
            "patient_gender": "F",
            "variant": "baseline",
        },
    )

    assert res.status_code == 200
    assert captured["use_phoenix_memory"] is False
    assert captured["playbook_override"]["version"] == "day_zero"
    assert captured["drafter_prompt_text"]


def test_measure_case_candidate_uses_live_prompt_and_phoenix(monkeypatch) -> None:
    captured: dict = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return type(
            "R",
            (),
            {
                "appeal_package": {
                    "appeal_package_draft": {"appeal_letter": "Dear insurer,"},
                    "trace_metadata": {"prompt_version": "drafter_v2"},
                    "risk_flags": [],
                },
                "outcome": {
                    "verdict": "APPROVE",
                    "score": 0.82,
                    "threshold": 0.7,
                    "feature_scores": [],
                    "gaps": [],
                    "critique": "",
                    "rationale": [],
                },
            },
        )()

    monkeypatch.setattr("app.aegis_v1.appeal_orchestrator.run_appeal_with_outcome", fake_run)

    client = _client()
    res = client.post(
        "/v1/showcase/measure-case",
        json={
            "case_id": "case_168_aetna_priorauth",
            "denial_letter_text": "Denied.",
            "clinical_context": "Notes.",
            "insurer": "Aetna",
            "denial_type": "Prior authorization",
            "patient_age": 53,
            "patient_gender": "F",
            "variant": "candidate",
        },
    )

    assert res.status_code == 200
    assert captured["use_phoenix_memory"] is True
    assert captured["playbook_override"] is None
    assert captured["drafter_prompt_text"] is None
