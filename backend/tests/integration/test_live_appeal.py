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
        clinical_context=(
            "Patient failed two adequate SSRI trials and documented severe, "
            "treatment-resistant depression."
        ),
        case_id="live_smoke",
    )

    letter = result.appeal_package["appeal_package_draft"]["appeal_letter"]
    assert letter.strip()
    # guardrail must hold even on real model prose
    assert "Not legal or medical advice" in letter
    assert "!" not in letter
    # a real outcome came back
    assert result.outcome["verdict"] in {"APPROVE", "DENY"}
    assert isinstance(result.outcome["score"], int)
    # weak-v1 demo arc: perfect-10 threshold means the baseline should DENY
    assert result.outcome["threshold"] == 10


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
        "patient_profile": {"plan_funding_type": "fully_insured"},
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
