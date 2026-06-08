#!/usr/bin/env python3
"""Smoke-test Phase 3 GEPA seed path on deployed aegis-v1-api.

Runs ``/v1/showcase/seed-smoke``: student pipeline → ADK judge workflow →
Phoenix annotation (no simulator). Synthetic case only.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

PAYLOAD = {
    "case_id": "prod_seed_smoke",
    "denial_letter_text": (
        "Cigna denied Intensive Outpatient Program because medical necessity "
        "was not demonstrated."
    ),
    "clinical_context": (
        "Severe OCD; six months of failed weekly outpatient therapy."
    ),
    "judge_mode": "official",
}


def main() -> int:
    base = (
        os.environ.get("AEGIS_API_URL")
        or (sys.argv[1] if len(sys.argv) > 1 else "")
    ).rstrip("/")
    if not base:
        print("Usage: AEGIS_API_URL=https://... smoke_prod_phase3_seed.py", file=sys.stderr)
        return 2

    url = f"{base}/v1/showcase/seed-smoke"
    req = urllib.request.Request(
        url,
        data=json.dumps(PAYLOAD).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        print("POST", url)
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

    print("trace_ref:", body.get("trace_ref"))
    print("verdict:", body.get("verdict"))
    print("weighted_quality:", body.get("weighted_quality"))
    print("judge_client:", body.get("judge_client"))
    print("phoenix_url:", body.get("phoenix_url"))

    failures: list[str] = []
    if not body.get("trace_ref"):
        failures.append("missing trace_ref")
    if body.get("judge_client") not in {"adk", "gemini"}:
        failures.append(f"unexpected judge_client={body.get('judge_client')!r}")
    if not body.get("phoenix_url"):
        failures.append("missing phoenix_url")

    if failures:
        print("FAIL:", ", ".join(failures), file=sys.stderr)
        return 1

    print("PASS: Phase 3 GEPA seed path on prod (/v1/showcase/seed-smoke)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
