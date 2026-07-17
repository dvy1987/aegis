#!/usr/bin/env python3
"""Re-score Measured Lift with the Outcome Simulator only (no drafter).

Uses existing ``appeal_letter`` from the ledger or a remote demo-state API,
then writes updated scores to ``measured_lift.json`` (local dir or GCS).

Usage (from repo root):
  set -a && source .env && set +a
  uv run --directory backend python scripts/rescore_lift_simulator.py \\
    --variant candidate --case case_168_aetna_priorauth --case case_180_cigna_mednec

  # Rescore via deployed API (after simulator-only measure-case is live):
  uv run --directory backend python scripts/rescore_lift_simulator.py \\
    --api https://aegis-v1-api-v6a3eydpoq-uc.a.run.app --variant candidate
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO = BACKEND_ROOT.parent
CASES_DIR = REPO / "eval" / "cases" / "drafts" / "showcase-eval"
DEFAULT_SOURCE_API = "https://aegis-v1-api-v6a3eydpoq-uc.a.run.app"
LIFT_CASES = (
    "case_168_aetna_priorauth",
    "case_180_cigna_mednec",
    "case_193_cigna_priorauth",
)

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _load_env() -> None:
    env_path = REPO / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        import os

        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _fetch_demo_state(api_base: str) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}/v1/showcase/demo-state"
    with urllib.request.urlopen(url, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_rescore(api_base: str, case: dict, variant: str, stored: dict[str, Any]) -> dict:
    profile = case.get("patient_profile") or {}
    letter = str(stored.get("appeal_letter") or "").strip()
    if not letter:
        raise ValueError(f"missing appeal_letter for {case['case_id']} ({variant})")
    payload = {
        "case_id": case["case_id"],
        "denial_letter_text": case["denial_letter_text"],
        "clinical_context": case.get("clinical_context") or "",
        "insurer": case["insurer"],
        "denial_type": case.get("denial_type") or "",
        "patient_age": int(profile.get("age") or 0),
        "patient_gender": str(profile.get("gender") or "X"),
        "variant": variant,
        "appeal_letter": letter,
        "prompt_version": stored.get("prompt_version"),
    }
    url = f"{api_base.rstrip('/')}/v1/showcase/measure-case"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _rescore_local(case: dict, variant: str, stored: dict[str, Any]) -> dict:
    from app.aegis_v1.showcase_api import ShowcaseMeasureRequest, _measure_simulator_only

    profile = case.get("patient_profile") or {}
    letter = str(stored.get("appeal_letter") or "").strip()
    if not letter:
        raise ValueError(f"missing appeal_letter for {case['case_id']} ({variant})")
    req = ShowcaseMeasureRequest(
        case_id=case["case_id"],
        denial_letter_text=case["denial_letter_text"],
        clinical_context=str(case.get("clinical_context") or ""),
        insurer=case["insurer"],
        denial_type=str(case.get("denial_type") or ""),
        patient_age=int(profile.get("age") or 0),
        patient_gender=str(profile.get("gender") or "X"),
        variant=variant,  # type: ignore[arg-type]
        appeal_letter=letter,
        prompt_version=stored.get("prompt_version"),
    )
    return _measure_simulator_only(req).model_dump()


def main() -> int:
    _load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api",
        default="",
        help="POST simulator-only rescore to this API (omit to run in-process)",
    )
    parser.add_argument(
        "--source-api",
        default=DEFAULT_SOURCE_API,
        help="Fetch existing appeal letters from this demo-state API",
    )
    parser.add_argument(
        "--variant",
        choices=("baseline", "candidate"),
        default="candidate",
        help="Which column to rescore (default: candidate / after learning)",
    )
    parser.add_argument("--case", action="append", dest="cases", help="Limit to case_id(s)")
    args = parser.parse_args()

    demo_state = _fetch_demo_state(args.source_api)
    measured_lift = demo_state.get("measured_lift") or {}
    case_ids = args.cases or list(LIFT_CASES)

    results: list[dict] = []
    for case_id in case_ids:
        path = CASES_DIR / f"{case_id}.json"
        if not path.is_file():
            print(f"SKIP missing {path}", file=sys.stderr)
            continue
        stored = (measured_lift.get(case_id) or {}).get(args.variant)
        if not stored:
            print(f"SKIP no stored {args.variant} for {case_id}", file=sys.stderr)
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        print(f"Rescoring {case_id} ({args.variant}) …", flush=True)
        try:
            if args.api:
                row = _post_rescore(args.api, case, args.variant, stored)
            else:
                row = _rescore_local(case, args.variant, stored)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            print(f"FAIL {case_id}: HTTP {exc.code} {body}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"FAIL {case_id}: {exc}", file=sys.stderr)
            return 1
        results.append(row)
        print(
            f"  → {row['verdict']} score={row['score']} threshold={row['threshold']} "
            f"prompt={row.get('prompt_version', '')}"
        )

    if not results:
        print("No cases rescored.", file=sys.stderr)
        return 1

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
