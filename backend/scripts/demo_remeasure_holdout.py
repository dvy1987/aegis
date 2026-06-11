#!/usr/bin/env python3
"""Re-run holdout post-measure with demo simulator; patch cloud session JSON.

Usage (from backend/, with .env loaded and GCP creds for GCS):

  export AEGIS_SHOWCASE_LEDGER_GCS_URI=gs://YOUR_BUCKET/aegis-showcase-ledger
  export AEGIS_SIMULATOR_PROFILE=demo
  uv run python scripts/demo_remeasure_holdout.py --session-id quick_20260611_103044_21916b

Dry-run (measure only, no GCS write):

  uv run python scripts/demo_remeasure_holdout.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--session-id",
        default="quick_20260611_103044_21916b",
        help="Showcase session to patch",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run measure and print verdict; do not write GCS",
    )
    args = parser.parse_args()

    os.environ.setdefault("AEGIS_SIMULATOR_PROFILE", "demo")
    gcs_uri = os.environ.get("AEGIS_SHOWCASE_LEDGER_GCS_URI", "").strip()
    if not args.dry_run and not gcs_uri:
        print(
            "Set AEGIS_SHOWCASE_LEDGER_GCS_URI (e.g. gs://bucket/aegis-showcase-ledger) "
            "or pass --dry-run",
            file=sys.stderr,
        )
        return 1

    from app.aegis_v1.drafter_client import (
        get_active_drafter_prompt_version,
        load_drafter_prompt,
    )
    from app.aegis_v1.showcase_ledger import open_ledger_store
    from app.aegis_v1.showcase_manifest import load_showcase_manifest
    from app.aegis_v1.showcase_runner import _case_obj, _case_slice
    from app.aegis_v1.showcase_session import ShowcaseSessionManager
    from app.aegis_v1.simulator_client import AdkSimulatorClient
    from app.evals.part_a.measurement_run import run_measurement_case

    manifest = load_showcase_manifest()
    manager = ShowcaseSessionManager(store=open_ledger_store())
    if args.dry_run:
        holdout_cases = manifest.quick_holdout
        run_type = "quick"
    else:
        session = manager.get(args.session_id)
        run_type = session.run_type
        holdout_cases = (
            manifest.quick_holdout
            if run_type == "quick"
            else manifest.serious_holdout
        )
    if not holdout_cases:
        print("No holdout cases in manifest", file=sys.stderr)
        return 1

    prompt_version = get_active_drafter_prompt_version()
    prompt_text = load_drafter_prompt(prompt_version)
    print(f"session={args.session_id} run_type={run_type} profile=demo holdout={len(holdout_cases)}")
    print(f"active_drafter={prompt_version}")

    results: list[dict] = []
    simulator = AdkSimulatorClient()
    for case in holdout_cases:
        teacher_case = case.judge_case(
            dataset_split=f"showcase_post_measure_{args.session_id}"
        )
        row = run_measurement_case(
            _case_obj(case, dataset_split=f"showcase_post_measure_{args.session_id}"),
            drafter_client=None,
            simulator_client=simulator,
            drafter_prompt_version=prompt_version,
            drafter_prompt_text=prompt_text,
            run_question_agent=True,
            teacher_clinical_context=str(teacher_case.get("clinical_context") or ""),
        )
        payload = row.model_dump()
        results.append(payload)
        print(f"  {case.case_id}: {payload['verdict']} score={payload['score']}")

    if args.dry_run:
        print("dry-run — GCS not updated")
        return 0

    session = manager.get(args.session_id)
    session.post_measure_results = results
    session.regression_detected = False
    session.regression_summary = None
    session.updated_at = _now()
    manager._save(session)
    print(f"patched post_measure_results on GCS ({gcs_uri})")
    print("Pull locally: uv run python scripts/pull_showcase_ledger.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
