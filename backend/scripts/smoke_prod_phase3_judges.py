#!/usr/bin/env python3
"""Smoke-test Phase 3 on a deployed aegis-v1-api: ADK judge-panel Workflow.

Hits ``/v1/showcase/judge-smoke`` with ``judge_mode=official`` so ``run_panel``
uses GeminiJudgeClient → AdkJudgeClient → ``judge_panel_workflow`` without the
latency of a full ``/evaluate`` double-pipeline pass.

Synthetic case only. No PHI.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

PAYLOAD = {
    "case_id": "prod_phase3_smoke",
    "denial_letter_text": (
        "Dear Member, Cigna has denied coverage for Intensive Outpatient Program "
        "for Obsessive-Compulsive Disorder because the service is not medically "
        "necessary based on the information submitted."
    ),
    "clinical_context": (
        "The person has severe OCD with daily compulsions lasting several hours. "
        "Six months of weekly outpatient therapy did not reduce symptoms."
    ),
    "judge_mode": "official",
}


def main() -> int:
    base = (
        os.environ.get("AEGIS_API_URL")
        or (sys.argv[1] if len(sys.argv) > 1 else "")
    ).rstrip("/")
    if not base:
        print(
            "Usage: AEGIS_API_URL=https://... smoke_prod_phase3_judges.py",
            file=sys.stderr,
        )
        return 2

    health_url = f"{base}/health"
    judge_url = f"{base}/v1/showcase/judge-smoke"
    req = urllib.request.Request(
        judge_url,
        data=json.dumps(PAYLOAD).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(health_url, timeout=30) as resp:
            health = json.loads(resp.read().decode())
        print("health:", health)
        print("POST", judge_url, "(judge_mode=official → ADK judge workflow)")
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = json.loads(resp.read().decode())
        elapsed = time.time() - t0
        print(f"elapsed: {elapsed:.1f}s")
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        print("HTTP error:", exc.code, body_text[:2000], file=sys.stderr)
        return 1
    except Exception as exc:
        print("Request failed:", exc, file=sys.stderr)
        return 1

    print("case_id:", body.get("case_id"))
    print("verdict:", body.get("verdict"))
    print("weighted_quality:", body.get("weighted_quality"))
    print("judge_client:", body.get("judge_client"))
    print("dimensions_scored:", body.get("dimensions_scored"))

    failures: list[str] = []
    if body.get("judge_client") not in {"adk", "gemini"}:
        failures.append(f"unexpected judge_client={body.get('judge_client')!r}")
    if body.get("dimensions_scored") != 7:
        failures.append(f"expected 7 judge dimensions, got {body.get('dimensions_scored')}")
    wq = body.get("weighted_quality")
    if wq is not None and not isinstance(wq, (int, float)):
        failures.append("weighted_quality is not numeric")
    if not body.get("dimension_scores"):
        failures.append("empty dimension_scores")

    if failures:
        print("FAIL:", ", ".join(failures), file=sys.stderr)
        return 1

    print("PASS: Phase 3 ADK judge workflow on prod (/v1/showcase/judge-smoke official)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
