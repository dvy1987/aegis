#!/usr/bin/env python3
"""Smoke-test /v1/showcase/evaluate on deployed aegis-v1-api (Phase 3 + pipeline).

Uses the same baseline and candidate prompt so the server runs one pipeline pass
and reuses the result for both sides.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

PAYLOAD = {
    "case_id": "prod_evaluate_smoke",
    "denial_letter_text": (
        "Cigna denied Intensive Outpatient Program for OCD as not medically necessary."
    ),
    "clinical_context": "Severe OCD with failed outpatient therapy.",
    "baseline_prompt_version": "drafter_v1",
    "candidate_prompt_version": "drafter_v1",
    "judge_mode": "official",
    "run_counterfactual": False,
}


def main() -> int:
    base = (
        os.environ.get("AEGIS_API_URL")
        or (sys.argv[1] if len(sys.argv) > 1 else "")
    ).rstrip("/")
    if not base:
        print("Usage: AEGIS_API_URL=https://... smoke_prod_showcase_evaluate.py", file=sys.stderr)
        return 2

    url = f"{base}/v1/showcase/evaluate"
    req = urllib.request.Request(
        url,
        data=json.dumps(PAYLOAD).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        print("POST", url, "(same prompt → single pipeline pass)")
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = json.loads(resp.read().decode())
        print(f"elapsed: {time.time() - t0:.1f}s")
    except urllib.error.HTTPError as exc:
        print("HTTP error:", exc.code, exc.read().decode(errors="replace")[:2000], file=sys.stderr)
        return 1
    except Exception as exc:
        print("Request failed:", exc, file=sys.stderr)
        return 1

    print("measured:", body.get("measured"))
    print("v1 composite:", body.get("v1", {}).get("composite"))
    print("v3 composite:", body.get("v3", {}).get("composite"))
    print("phoenix_url:", body.get("phoenix_url"))

    failures: list[str] = []
    if not body.get("measured"):
        failures.append("measured=false")
    if not body.get("phoenix_url"):
        failures.append("missing phoenix_url")
    v1c = body.get("v1", {}).get("composite")
    if not isinstance(v1c, (int, float)):
        failures.append("v1 missing composite")

    if failures:
        print("FAIL:", ", ".join(failures), file=sys.stderr)
        return 1

    print("PASS: showcase evaluate on prod (/v1/showcase/evaluate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
