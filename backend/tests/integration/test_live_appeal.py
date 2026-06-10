"""Live, GCP-only integration tests for the product appeal path.

These exercise the REAL Vertex/Gemini drafter + Outcome Simulator end-to-end (no
stubs). They auto-skip when no Application Default Credentials are available, so
they are safe to run on this offline dev machine and ready to run on the wired
machine simply with:

    cd backend && env UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/integration -q

When ADC/Vertex is configured, they validate that a real draft is produced, the
guardrail held on real model prose, and the simulator returns a real verdict.
"""
from __future__ import annotations

import pytest


def _adc_available() -> bool:
    try:
        import google.auth

        google.auth.default()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _adc_available(),
    reason="No GCP ADC; live Vertex test skipped — run on the machine where GCP is wired.",
)


def test_live_appeal_run_produces_letter_and_outcome():
    from app.aegis_v1.appeal_orchestrator import run_appeal_with_outcome

    result = run_appeal_with_outcome(
        denial_text=(
            "We denied coverage for TMS for treatment-resistant depression as not "
            "medically necessary. You may appeal within 180 days."
        ),
        clinical_context="Patient age: 45. Patient gender: female.",
        case_id="live_smoke",
        insurer="Cigna",
        patient_age=45,
        patient_gender="F",
    )

    letter = result.appeal_package["appeal_package_draft"]["appeal_letter"]
    assert letter.strip()
    # guardrail must hold even on real model prose
    assert "Not legal or medical advice" in letter
    assert "!" not in letter
    # a real outcome came back, scored deterministically from LLM features
    assert result.outcome["verdict"] in {"APPROVE", "DENY"}
    assert 0.0 <= result.outcome["score"] <= 1.0
    assert result.outcome["threshold"] == 0.80
    assert result.outcome["feature_scores"]  # transparent breakdown present


def test_live_evaluated_case_writes_real_phoenix_annotation():
    """The eval loop against a real Phoenix project (OtelPhoenixRecorder) + live
    simulator. Requires both GCP ADC and a reachable Phoenix endpoint."""
    from app.aegis_v1.simulator_client import GeminiSimulatorClient
    from app.evals.part_a.evaluated_run import run_evaluated_case
    from app.evals.part_a.recorder import OtelPhoenixRecorder

    case = {
        "case_id": "live_eval_smoke", "insurer": "Cigna", "denial_type": "Medical Necessity",
        "denial_letter_text": "We denied coverage for TMS as not medically necessary.",
        "clinical_context": "Patient failed two SSRIs; severe treatment-resistant depression.",
        "patient_profile": {
            "age": 45,
            "gender": "F",
            "plan_funding_type": "fully_insured",
        },
        "denial_pattern_sources": [], "synthetic_provenance": {"appeal_difficulty": {}},
    }
    result = run_evaluated_case(
        case,
        recorder=OtelPhoenixRecorder(),
        run_simulator=True,
        simulator_client=GeminiSimulatorClient(),
    )
    assert result.panel_report.verdict in {"PASS", "FAIL"}
    assert result.simulator_result["verdict"] in {"APPROVE", "DENY"}
    assert result.trace_ref  # a real span id was emitted
