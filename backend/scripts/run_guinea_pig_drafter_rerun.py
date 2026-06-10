#!/usr/bin/env python3
"""Re-run drafter + simulator using a saved question interview (no re-interview).

Usage:
    uv run python scripts/run_guinea_pig_drafter_rerun.py \\
        --interview ../eval/GUINEA-PIG-RUNS/.../question_interview.json \\
        --case ../eval/cases/drafts/guinea-pigs/case_127_aetna_priorauth.json
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / "eval" / "GUINEA-PIG-RUNS"

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
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")


def main() -> None:
    parser = argparse.ArgumentParser(description="Drafter+sim rerun from saved interview.")
    parser.add_argument("--case", required=True)
    parser.add_argument("--interview", required=True)
    args = parser.parse_args()

    _load_env()
    try:
        import google.auth

        google.auth.default()
    except Exception as exc:
        sys.exit(f"Google ADC missing: {exc}")

    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    interview = json.loads(Path(args.interview).read_text(encoding="utf-8"))
    case_id = str(case.get("case_id") or "guinea_pig")

    from app.aegis_v1.appeal_orchestrator import run_appeal_with_outcome
    from app.aegis_v1.patient_context import pipeline_inputs_from_case
    from app.aegis_v1.question_agent import refresh_interview_artifact
    from app.aegis_v1.simulator_client import AdkSimulatorClient

    student_inputs = pipeline_inputs_from_case(case)
    refreshed = refresh_interview_artifact(interview, notes=student_inputs["clinical_context"])

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUTPUT_ROOT / f"{case_id}_drafter_rerun_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    token_records: list[dict] = []
    import app.gemini_retry as gr

    original = gr.generate_content_with_fallback

    def tracking_fallback(generate_content, *, model: str, fallback_model=None, **kwargs):
        response = original(
            generate_content, model=model, fallback_model=fallback_model, **kwargs
        )
        usage = getattr(response, "usage_metadata", None)
        token_records.append(
            {
                "model": model,
                "prompt_tokens": int(getattr(usage, "prompt_token_count", 0) or 0),
                "output_tokens": int(getattr(usage, "candidates_token_count", 0) or 0),
            }
        )
        return response

    gr.generate_content_with_fallback = tracking_fallback

    appeal = run_appeal_with_outcome(
        **student_inputs,
        dataset_split="guinea_pig_drafter_rerun",
        run_mode="benchmark",
        drafter_client=None,
        simulator_client=AdkSimulatorClient(),
        question_interview=refreshed,
    )

    package = appeal.appeal_package
    sim = appeal.outcome
    letter = str(package.get("appeal_package_draft", {}).get("appeal_letter") or "")

    measurement = {
        "case_id": case_id,
        "verdict": sim["verdict"],
        "score": float(sim["score"]),
        "threshold": float(sim["threshold"]),
        "prompt_version": str((package.get("trace_metadata") or {}).get("prompt_version") or ""),
        "risk_flags": list(package.get("risk_flags") or []),
    }

    (out_dir / "question_interview_refreshed.json").write_text(
        json.dumps(refreshed, indent=2, default=str), encoding="utf-8"
    )
    (out_dir / "appeal_package.json").write_text(
        json.dumps(package, indent=2, default=str), encoding="utf-8"
    )
    (out_dir / "appeal_letter.txt").write_text(letter, encoding="utf-8")
    (out_dir / "simulator_outcome.json").write_text(
        json.dumps(sim, indent=2, default=str), encoding="utf-8"
    )
    (out_dir / "measurement_result.json").write_text(
        json.dumps(measurement, indent=2), encoding="utf-8"
    )
    (out_dir / "token_calls.json").write_text(
        json.dumps(token_records, indent=2), encoding="utf-8"
    )
    (out_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "run_type": "drafter_rerun_from_interview",
                "source_interview": str(Path(args.interview)),
                "case_path": str(Path(args.case)),
                "timestamp_utc": stamp,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(json.dumps({"output_dir": str(out_dir), **measurement}, indent=2))


if __name__ == "__main__":
    main()
