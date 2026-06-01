"""Phase-2 efficacy run — input prep (firewall enforcement).

Emits, for the selected train/held-out cases:
  inputs/student_<case_id>.json  — firewall-CLEAN drafter input (build_student_case_packet):
                                    case_id + denial_letter_text + clinical_context only.
  inputs/teacher_<case_id>.json  — teacher answer-key packet (build_teacher_grading_packet),
                                    given ONLY to judge subagents.
  inputs/manifest.json           — train/holdout split + per-case insurer/denial_type.

Run from backend/:  env UV_CACHE_DIR=/tmp/uv-cache uv run python \
                        ../eval/efficacy_runs/2026-05-31/prep_inputs.py
The firewall is enforced by reusing the production packet builders (via
app.learning.efficacy_io.build_run_inputs) — synthetic_provenance (the answer
key) never enters a student packet.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.evals.part_a.teacher_packet import load_case
from app.learning.efficacy_io import build_run_inputs

RUN_DIR = Path(__file__).resolve().parent
REPO = RUN_DIR.parents[2]
CASES = REPO / "eval" / "cases" / "drafts"
OUT = RUN_DIR / "inputs"

TRAIN = [
    "case_01_cigna_mednec",
    "case_03_aetna_mednec",
    "case_05_uhc_mednec",
    "case_02_cigna_priorauth",
]
HELDOUT = [
    "test_case_01_uhc_mednec",
    "test_case_02_aetna_priorauth",
    "test_case_03_cigna_mednec",
    "test_case_04_uhc_priorauth",
]


def main() -> None:
    # Firewall-clean student packets + teacher packets (reuses the production builders).
    build_run_inputs(TRAIN + HELDOUT, cases_dir=CASES, out_dir=RUN_DIR)
    # Run manifest (split + light metadata; no answer-key fields).
    manifest = {"train": TRAIN, "holdout": HELDOUT, "cases": {}}
    for case_id in TRAIN + HELDOUT:
        case = load_case(CASES / f"{case_id}.json")
        manifest["cases"][case_id] = {
            "insurer": case.get("insurer"),
            "denial_type": case.get("denial_type"),
            "split": "train" if case_id in TRAIN else "holdout",
        }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(TRAIN + HELDOUT)} student+teacher packets to {OUT}")
    print(f"  train={len(TRAIN)} holdout={len(HELDOUT)}")


if __name__ == "__main__":
    main()
