"""Live LearningCoordinator CLI (Tier 1 Phase E).

Wires `LivePhoenixLearningStore` + `LiveExperimentRunner(GeminiDrafterClient,
PanelJudgeAdapter(GeminiJudgeClient))` + `GeminiReflectionClient` into the
`LearningCoordinator` so a single command runs one round of GEPA over real
Phoenix signal and real Gemini drafts/judges, then prints a `PromotionProposal`
as a HITL card. Promotion is gated on `--promote --approver`.

Usage from backend/:
    # Seed real spans first if the slice is empty:
    env UV_CACHE_DIR=/tmp/uv-cache uv run python -m app.learning.run_live --record-only

    # Optimize one slice and dry-run print the proposal:
    env UV_CACHE_DIR=/tmp/uv-cache uv run python -m app.learning.run_live \
        --slice Cigna:medical_necessity

    # After PM approval, promote:
    env UV_CACHE_DIR=/tmp/uv-cache uv run python -m app.learning.run_live \
        --slice Cigna:medical_necessity --promote --approver pm@aegis

Required env (loaded from `.env`): `PHOENIX_API_KEY`, `PHOENIX_HOST`,
`GOOGLE_CLOUD_PROJECT`, GCP ADC. The CLI fails fast if any are missing.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


# Mirror the IPv4-first patch used by main_v1.py and the seed script so
# phoenix.client and Vertex don't hang on macOS IPv6 resolution.
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_first_getaddrinfo


def _load_env() -> None:
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    if "PHOENIX_API_KEY" not in os.environ:
        sys.exit("PHOENIX_API_KEY missing; populate .env first.")
    os.environ.setdefault("PHOENIX_PROJECT_NAME", "default")
    if "PHOENIX_CLIENT_HEADERS" not in os.environ:
        os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={os.environ['PHOENIX_API_KEY']}"
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")


def _creds_available() -> bool:
    """Return True iff PHOENIX_API_KEY + Google ADC are both present.

    Mirrors `tests/integration/test_live_appeal.py::_adc_available()`, used as
    the gate for the live integration test in this module's test suite."""
    if not os.environ.get("PHOENIX_API_KEY"):
        return False
    try:
        import google.auth

        google.auth.default()
        return True
    except Exception:
        return False


def _benchmark_dataset(slice_filter: str) -> list[dict[str, Any]]:
    """Build the per-case dataset that LiveExperimentRunner expects, filtered to
    `slice_filter` (e.g. 'Cigna:medical_necessity'). Pulls cases from
    `eval/cases/drafts/` and reads the Phoenix-memory summary live so the
    drafter sees the same context the product surface gets."""
    from app.aegis_v1.tools import case_parser, phoenix_mcp_lookup

    cases_dir = REPO_ROOT / "eval" / "cases" / "drafts"
    insurer, denial = slice_filter.split(":", 1)
    dataset: list[dict[str, Any]] = []
    for path in sorted(cases_dir.glob("case_*.json")):
        case = json.loads(path.read_text())
        if (case.get("insurer") or "").lower() != insurer.lower():
            continue
        denial_norm = (case.get("denial_type") or "").replace(" ", "_").lower()
        if denial.lower() not in denial_norm:
            continue
        parsed = case_parser(
            denial_text=case.get("denial_letter_text", ""),
            clinical_context=case.get("clinical_context", ""),
            case_id=case.get("case_id", path.stem),
        )
        dataset.append({
            "case_id": case["case_id"],
            "slice": slice_filter,
            "parsed_case": parsed,
            "citations": [],
            "phoenix_summary": phoenix_mcp_lookup(
                insurer=parsed["insurer"],
                denial_type=parsed["denial_type"],
                case_id=parsed["case_id"],
            ),
            # Carry the original case for the judge panel adapter.
            "denial_letter_text": case.get("denial_letter_text", ""),
            "clinical_context": case.get("clinical_context", ""),
            "expected_appeal_vectors": case.get("expected_appeal_vectors", []),
            "exploitable_weaknesses": case.get("exploitable_weaknesses", []),
            "patient_profile": case.get("patient_profile", {}),
            "matrix_cell": case.get("matrix_cell", {}),
            "denial_pattern_sources": case.get("denial_pattern_sources", []),
            "submission_timestamp": case.get("submission_timestamp"),
            "denial_timestamp": case.get("denial_timestamp"),
        })
    return dataset


def build_live_coordinator(slice_filter: str, *, max_rounds: int = 1):
    """Construct the live coordinator object graph. Cloud SDK imports are
    method-local so this function imports cleanly when called from tests."""
    from app.aegis_v1.drafter_client import GeminiDrafterClient
    from app.evals.part_a.llm_judges import GeminiJudgeClient
    from app.learning.coordinator import LearningCoordinator
    from app.learning.experiment import LiveExperimentRunner
    from app.learning.judge_adapter import PanelJudgeAdapter
    from app.learning.phoenix_live import LivePhoenixLearningStore
    from app.learning.reflection_client import GeminiReflectionClient

    store = LivePhoenixLearningStore()
    dataset = _benchmark_dataset(slice_filter)
    runner = LiveExperimentRunner(
        dataset=dataset,
        drafter_client=GeminiDrafterClient(),
        judge_client=PanelJudgeAdapter(judge_client=GeminiJudgeClient()),
    )
    return LearningCoordinator(
        store=store,
        runner=runner,
        reflection_client=GeminiReflectionClient(),
        slice_filter=slice_filter,
        max_rounds=max_rounds,
    )


def _record_only(slice_filter: str | None) -> None:
    """Fire one `run_evaluated_case` per matching benchmark case so the slice
    has fresh Phoenix signal before the optimizer runs."""
    from app.aegis_v1.drafter_client import GeminiDrafterClient
    from app.app_utils.telemetry import setup_telemetry
    from app.evals.part_a.evaluated_run import run_evaluated_case
    from app.evals.part_a.recorder import OtelPhoenixRecorder

    setup_telemetry()
    recorder = OtelPhoenixRecorder(project_name=os.environ["PHOENIX_PROJECT_NAME"])
    drafter = GeminiDrafterClient()
    cases_dir = REPO_ROOT / "eval" / "cases" / "drafts"
    seeded = 0
    for path in sorted(cases_dir.glob("case_*.json")):
        case = json.loads(path.read_text())
        case["dataset_split"] = "benchmark_train"
        if slice_filter:
            insurer, denial = slice_filter.split(":", 1)
            if (case.get("insurer") or "").lower() != insurer.lower():
                continue
            denial_norm = (case.get("denial_type") or "").replace(" ", "_").lower()
            if denial.lower() not in denial_norm:
                continue
        run_evaluated_case(case, recorder=recorder, drafter_client=drafter, run_simulator=False)
        seeded += 1
        if seeded >= 5:
            break
    print(f"Seeded {seeded} cases into Phoenix project "
          f"{os.environ['PHOENIX_PROJECT_NAME']}.")


def _print_proposal(proposal) -> None:
    if proposal is None:
        print(json.dumps({"status": "no_signal", "reason": "INV-1 halt"}))
        return
    print(json.dumps({
        "status": "proposal",
        "before_composite": proposal.before.composite,
        "after_composite": proposal.after.composite,
        "delta": round(proposal.after.composite - proposal.before.composite, 4),
        "vetoes": proposal.vetoes,
        "is_promotable": proposal.is_promotable,
        "candidate_id": proposal.candidate.candidate_id,
        "diff_summary": proposal.candidate.diff_summary,
        "per_dimension_deltas": proposal.per_dimension_deltas,
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Live LearningCoordinator over real Phoenix.")
    parser.add_argument("--slice", default=None, help="e.g. Cigna:medical_necessity")
    parser.add_argument("--record-only", action="store_true",
                        help="Only seed Phoenix with run_evaluated_case for the slice.")
    parser.add_argument("--promote", action="store_true",
                        help="Promote the proposal (requires --approver).")
    parser.add_argument("--approver", default=None)
    parser.add_argument("--max-rounds", type=int, default=1)
    args = parser.parse_args()

    _load_env()
    if not _creds_available():
        sys.exit("Live run requires PHOENIX_API_KEY and Google ADC.")

    if args.record_only:
        _record_only(args.slice)
        return

    if not args.slice:
        sys.exit("--slice is required (e.g. Cigna:medical_necessity).")

    coordinator = build_live_coordinator(args.slice, max_rounds=args.max_rounds)
    proposal = coordinator.optimize()
    _print_proposal(proposal)

    if args.promote:
        if proposal is None or not proposal.is_promotable:
            sys.exit("Cannot promote: no promotable proposal.")
        if not args.approver:
            sys.exit("--promote requires --approver <name>.")
        coordinator.promote(proposal, approver=args.approver)
        print(json.dumps({"status": "promoted", "approver": args.approver}))


if __name__ == "__main__":
    main()
