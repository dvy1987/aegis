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
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / "eval" / "GUINEA-PIG-RUNS"

# Rough Vertex list prices (USD per 1M tokens) — estimates only; verify on your bill.
_PRICE_PER_M = {
    "gemini-3.1-pro-preview": {"input": 1.25, "output": 5.00},
    "gemini-3.5-flash": {"input": 0.15, "output": 0.60},
    "default": {"input": 1.25, "output": 5.00},
}

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
    os.environ.setdefault("PHOENIX_PROJECT_NAME", "default")
    if os.environ.get("PHOENIX_API_KEY") and "PHOENIX_CLIENT_HEADERS" not in os.environ:
        os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={os.environ['PHOENIX_API_KEY']}"
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")


def _install_token_tracker() -> list[dict[str, Any]]:
    """Patch Gemini calls to record usage_metadata from every response."""
    import app.gemini_retry as gr

    records: list[dict[str, Any]] = []
    original = gr.generate_content_with_fallback

    def tracking_fallback(generate_content, *, model: str, fallback_model=None, **kwargs):
        response = original(
            generate_content,
            model=model,
            fallback_model=fallback_model,
            **kwargs,
        )
        usage = getattr(response, "usage_metadata", None)
        prompt_t = int(getattr(usage, "prompt_token_count", 0) or 0)
        output_t = int(getattr(usage, "candidates_token_count", 0) or 0)
        total_t = int(getattr(usage, "total_token_count", 0) or 0) or (prompt_t + output_t)
        records.append(
            {
                "model": model,
                "prompt_tokens": prompt_t,
                "output_tokens": output_t,
                "total_tokens": total_t,
            }
        )
        return response

    gr.generate_content_with_fallback = tracking_fallback
    return records


def _estimate_cost_usd(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, dict[str, int]] = {}
    for row in records:
        model = str(row.get("model") or "default")
        bucket = by_model.setdefault(
            model,
            {"calls": 0, "prompt_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
        bucket["calls"] += 1
        bucket["prompt_tokens"] += int(row.get("prompt_tokens") or 0)
        bucket["output_tokens"] += int(row.get("output_tokens") or 0)
        bucket["total_tokens"] += int(row.get("total_tokens") or 0)

    total_usd = 0.0
    model_costs: dict[str, Any] = {}
    for model, counts in by_model.items():
        rates = _PRICE_PER_M.get(model) or _PRICE_PER_M["default"]
        input_usd = counts["prompt_tokens"] / 1_000_000 * rates["input"]
        output_usd = counts["output_tokens"] / 1_000_000 * rates["output"]
        subtotal = round(input_usd + output_usd, 6)
        total_usd += subtotal
        model_costs[model] = {**counts, "estimated_usd": round(subtotal, 6)}

    return {
        "gemini_calls": len(records),
        "per_model": model_costs,
        "total_prompt_tokens": sum(r.get("prompt_tokens", 0) for r in records),
        "total_output_tokens": sum(r.get("output_tokens", 0) for r in records),
        "total_tokens": sum(r.get("total_tokens", 0) for r in records),
        "estimated_total_usd": round(total_usd, 4),
        "pricing_note": "Estimated from public list prices; verify against GCP billing.",
        "per_call": records,
    }


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
**Estimated Gemini cost:** ${cost['estimated_total_usd']} ({cost['total_tokens']} tokens, {cost['gemini_calls']} calls)

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

    _load_env()
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

    token_records = _install_token_tracker()

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
    cost = _estimate_cost_usd(token_records)

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
