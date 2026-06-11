#!/usr/bin/env python3
"""Re-run Measured Lift simulator for showcase-eval cases (updates measured_lift.json).

Calls POST /v1/showcase/measure-case on the deployed API (or local).

Usage (from repo root):
  uv run --directory backend python scripts/remeasure_lift_cases.py
  uv run --directory backend python scripts/remeasure_lift_cases.py --api http://127.0.0.1:8001 --variant candidate
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CASES_DIR = REPO / "eval" / "cases" / "drafts" / "showcase-eval"
DEFAULT_API = "https://aegis-v1-api-v6a3eydpoq-uc.a.run.app"
LIFT_CASES = (
    "case_168_aetna_priorauth",
    "case_180_cigna_mednec",
    "case_193_cigna_priorauth",
)


def _post_measure(api_base: str, case: dict, variant: str) -> dict:
    profile = case.get("patient_profile") or {}
    payload = {
        "case_id": case["case_id"],
        "denial_letter_text": case["denial_letter_text"],
        "clinical_context": case.get("clinical_context") or "",
        "insurer": case["insurer"],
        "denial_type": case.get("denial_type") or "",
        "patient_age": int(profile.get("age") or 0),
        "patient_gender": str(profile.get("gender") or "X"),
        "variant": variant,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-measure Measured Lift showcase cases.")
    parser.add_argument("--api", default=DEFAULT_API, help="v1 API base URL")
    parser.add_argument(
        "--variant",
        choices=("baseline", "candidate", "both"),
        default="both",
        help="Which column to re-run (default: both)",
    )
    parser.add_argument("--case", action="append", dest="cases", help="Limit to case_id(s)")
    args = parser.parse_args()

    case_ids = args.cases or list(LIFT_CASES)
    variants = ["baseline", "candidate"] if args.variant == "both" else [args.variant]

    results: list[dict] = []
    for case_id in case_ids:
        path = CASES_DIR / f"{case_id}.json"
        if not path.is_file():
            print(f"SKIP missing {path}", file=sys.stderr)
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        for variant in variants:
            print(f"Measuring {case_id} ({variant}) …", flush=True)
            try:
                row = _post_measure(args.api, case, variant)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:400]
                print(f"FAIL {case_id} {variant}: HTTP {exc.code} {body}", file=sys.stderr)
                return 1
            except Exception as exc:
                print(f"FAIL {case_id} {variant}: {exc}", file=sys.stderr)
                return 1
            results.append(row)
            print(
                f"  → {row['verdict']} score={row['score']} threshold={row['threshold']} "
                f"prompt={row.get('prompt_version', '')}"
            )

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
