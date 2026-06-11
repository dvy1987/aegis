#!/usr/bin/env python3
"""Measure-only guinea pig run: question agent + drafter + simulator (no judges/GEPA).

Writes all artifacts under eval/GUINEA-PIG-RUNS/<case_id>_<timestamp>/ and
records per-call Gemini token usage + estimated USD cost.

Usage (from backend/):
    env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/run_guinea_pig_measure.py \\
        --case /path/to/case.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from guinea_pig_common import (
    OUTPUT_ROOT,
    REPO_ROOT,
    apply_ipv4_patch,
    estimate_cost_usd,
    install_token_tracker,
    load_env,
)

apply_ipv4_patch()


def _transcript_text(interview: dict[str, Any] | None) -> str:
    if not interview:
        return "(no question interview — question agent did not run or produced no artifact)\n"
    lines = [
        f"skipped: {interview.get('skipped')}",
        f"planned_questions: {len(interview.get('planned_questions') or [])}",
        "",
        "=== Q&A TRANSCRIPT ===",
    ]
    for turn in interview.get("qa_transcript") or []:
        lines.append(f"Q{turn.get('turn', '?')}: {turn.get('question', '')}")
        lines.append(f"A{turn.get('turn', '?')}: {turn.get('answer', '')}")
        lines.append("")
    lines.append("=== SUBSTANTIVE (to drafter) ===")
    for q in interview.get("substantive_questions") or []:
        lines.append(f"- {q}")
    lines.append("")
    lines.append("=== GAPS (draft page) ===")
    for q in interview.get("gap_questions") or []:
        lines.append(f"- {q}")
    lines.append("")
    lines.append("=== ENRICHED CONTEXT (fed to drafter) ===")
    lines.append(str(interview.get("enriched_context") or ""))
    return "\n".join(lines) + "\n"


def _summary_md(
    *,
    case_id: str,
    measurement: dict[str, Any],
    cost: dict[str, Any],
    out_dir: Path,
    interview: dict[str, Any] | None,
) -> str:
    turns = len((interview or {}).get("qa_transcript") or [])
    return f"""# Guinea pig measure run — {case_id}

**Verdict:** {measurement['verdict']}  
**Score:** {measurement['score']} (threshold {measurement['threshold']})  
**Prompt version:** {measurement.get('prompt_version', '')}  
**Question turns:** {turns}  
**Estimated Gemini cost:** ${cost['estimated_total_usd']} ({cost['total_tokens']} tokens, {cost['gemini_calls']} tracked calls)

Artifacts in `{out_dir.relative_to(REPO_ROOT)}`:

- `appeal_letter.txt` — draft letter
- `question_interview.json` — full interview artifact
- `question_transcript.txt` — readable Q&A
- `appeal_package.json` — full student output
- `simulator_outcome.json` — simulator breakdown
- `measurement_result.json` — headline scores
- `cost_summary.json` — token + USD estimate per call
- `summary.md` — this file

Not legal or medical advice. Draft assistance only.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Guinea pig measure-only run.")
    parser.add_argument(
        "--case",
        default=str(
            REPO_ROOT
            / "eval/cases/drafts/guinea-pigs/case_127_aetna_priorauth.json"
        ),
    )
    args = parser.parse_args()

    load_env()
    token_records = install_token_tracker()

    try:
        import google.auth

        google.auth.default()
    except Exception as exc:
        sys.exit(f"Google ADC missing: {exc}")

    case_path = Path(args.case)
    case = json.loads(case_path.read_text(encoding="utf-8"))
    case_id = str(case.get("case_id") or case_path.stem)
    case["dataset_split"] = "guinea_pig_measure"

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_ROOT / f"{case_id}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    from app.aegis_v1.appeal_orchestrator import run_appeal_with_outcome
    from app.aegis_v1.patient_context import pipeline_inputs_from_case
    from app.aegis_v1.simulator_client import AdkSimulatorClient

    teacher_clinical = str(case.get("clinical_context") or "")
    student_case = dict(case)
    student_case["dataset_split"] = "guinea_pig_measure"

    appeal = run_appeal_with_outcome(
        **pipeline_inputs_from_case(student_case),
        dataset_split="guinea_pig_measure",
        run_mode="benchmark",
        drafter_client=None,
        simulator_client=AdkSimulatorClient(),
        run_question_agent=True,
        teacher_clinical_context=teacher_clinical,
        patient_profile=case.get("patient_profile"),
    )
    package = appeal.appeal_package
    sim = appeal.outcome
    interview = package.get("question_interview")

    letter = str(package.get("appeal_package_draft", {}).get("appeal_letter") or "")
    excerpt = " ".join(letter.split())[:520]
    if len(letter) > 520:
        excerpt += "..."

    measurement = {
        "case_id": case_id,
        "verdict": sim["verdict"],
        "score": float(sim["score"]),
        "threshold": float(sim["threshold"]),
        "prompt_version": str((package.get("trace_metadata") or {}).get("prompt_version") or ""),
        "risk_flags": list(package.get("risk_flags") or []),
        "letter_excerpt": excerpt,
    }
    cost = estimate_cost_usd(token_records)

    (out_dir / "measurement_result.json").write_text(
        json.dumps(measurement, indent=2), encoding="utf-8"
    )
    (out_dir / "simulator_outcome.json").write_text(
        json.dumps(sim, indent=2, default=str), encoding="utf-8"
    )
    (out_dir / "appeal_package.json").write_text(
        json.dumps(package, indent=2, default=str), encoding="utf-8"
    )
    (out_dir / "appeal_letter.txt").write_text(
        str(package.get("appeal_package_draft", {}).get("appeal_letter") or ""),
        encoding="utf-8",
    )
    (out_dir / "question_interview.json").write_text(
        json.dumps(interview, indent=2, default=str), encoding="utf-8"
    )
    (out_dir / "question_transcript.txt").write_text(
        _transcript_text(interview), encoding="utf-8"
    )
    (out_dir / "cost_summary.json").write_text(
        json.dumps(cost, indent=2), encoding="utf-8"
    )
    (out_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "case_path": str(case_path),
                "case_id": case_id,
                "run_type": "measure_only",
                "question_agent": True,
                "judges": False,
                "gepa": False,
                "timestamp_utc": stamp,
                "estimated_cost_usd": cost["estimated_total_usd"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "summary.md").write_text(
        _summary_md(
            case_id=case_id,
            measurement=measurement,
            cost=cost,
            out_dir=out_dir,
            interview=interview,
        ),
        encoding="utf-8",
    )

    print(json.dumps({"output_dir": str(out_dir), **measurement, "cost": cost}, indent=2))


if __name__ == "__main__":
    main()
