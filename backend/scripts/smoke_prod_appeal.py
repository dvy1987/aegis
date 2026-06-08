#!/usr/bin/env python3
"""Smoke-test a deployed aegis-v1-api /v1/appeal endpoint (synthetic case only)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PAYLOAD = {
    "denial_text": (
        "Cigna denied Intensive Outpatient Program for Obsessive-Compulsive Disorder "
        "because medical necessity was not shown. You may appeal within 180 days."
    ),
    "clinical_context": (
        "Severe OCD with daily compulsions lasting several hours after failed "
        "outpatient therapy."
    ),
    "case_id": "prod_smoke_synthetic",
    "discovery_enabled": False,
}


def main() -> int:
    base = (os.environ.get("AEGIS_API_URL") or sys.argv[1] if len(sys.argv) > 1 else "").rstrip("/")
    if not base:
        print("Usage: AEGIS_API_URL=https://... smoke_prod_appeal.py", file=sys.stderr)
        return 2

    health_url = f"{base}/health"
    appeal_url = f"{base}/v1/appeal"
    req = urllib.request.Request(
        appeal_url,
        data=json.dumps(PAYLOAD).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(health_url, timeout=30) as resp:
            health = json.loads(resp.read().decode())
        print("health:", health)
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print("HTTP error:", exc.code, exc.read().decode(), file=sys.stderr)
        return 1
    except Exception as exc:
        print("Request failed:", exc, file=sys.stderr)
        return 1

    letter = body.get("appeal_letter", "")
    print("run_id:", body.get("run_id"))
    print("verdict:", body.get("outcome", {}).get("verdict"))
    print("letter_excerpt:", letter[:240].replace("\n", " "))
    failures: list[str] = []
    if not letter.strip():
        failures.append("empty appeal_letter")
    if "echo:" in letter.lower():
        failures.append("letter contains echo: (offline EchoLlm leaked to prod)")
    if "Not legal or medical advice" not in letter:
        failures.append("missing safety disclaimer")
    if failures:
        print("FAIL:", ", ".join(failures), file=sys.stderr)
        return 1
    print("PASS: prod /v1/appeal smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
