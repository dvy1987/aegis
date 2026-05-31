"""Phase-2 efficacy run — input prep (firewall enforcement).

Emits, for the selected train/held-out cases:
  inputs/student_<case_id>.json  — firewall-CLEAN drafter input (build_student_case_packet):
                                    case_id + denial_letter_text + clinical_context only.
  inputs/teacher_<case_id>.json  — teacher answer-key packet (build_teacher_grading_packet),
                                    given ONLY to judge subagents.

Run from backend/:  env UV_CACHE_DIR=/tmp/uv-cache uv run python \
                        ../eval/efficacy_runs/2026-05-31/prep_inputs.py
The firewall is enforced by reusing the production packet builders — synthetic_provenance
(the answer key) never enters a student packet.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.evals.part_a.teacher_packet import (
    build_student_case_packet,
    build_teacher_grading_packet,
    load_case,
)

REPO = Path(__file__).resolve().parents[3]
CASES = REPO / "eval" / "cases" / "drafts"
OUT = Path(__file__).resolve().parent / "inputs"

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
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"train": TRAIN, "holdout": HELDOUT, "cases": {}}
    for case_id in TRAIN + HELDOUT:
        case = load_case(CASES / f"{case_id}.json")
        student = build_student_case_packet(case)
        teacher = build_teacher_grading_packet(case)
        (OUT / f"student_{case_id}.json").write_text(
            student.model_dump_json(indent=2), encoding="utf-8"
        )
        (OUT / f"teacher_{case_id}.json").write_text(
            teacher.model_dump_json(indent=2), encoding="utf-8"
        )
        # firewall assertion: no answer-key string leaked into the student packet
        blob = student.model_dump_json()
        for forbidden in ("exploitable_weaknesses", "expected_appeal_vectors",
                          "appeal_difficulty", "synthetic_provenance", "strong_defenses"):
            assert forbidden not in blob, f"firewall breach: {forbidden} in student_{case_id}"
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
