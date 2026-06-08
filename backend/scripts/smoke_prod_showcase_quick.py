#!/usr/bin/env python3
"""Smoke-test full quick showcase on deployed aegis-v1-api (Phase 4 exit).

Starts ``POST /v1/showcase/runs/quick`` and polls until ``needs_approval``,
``successful``, or ``failed``. Expect 60–120+ minutes on prod (live Gemini).
"""
from __future__ import annotations

import json
import os
import sys
import time

# Line-buffer stdout when polling for long runs (non-TTY).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
import urllib.error
import urllib.request

DEFAULT_TIMEOUT_S = int(os.environ.get("SHOWCASE_QUICK_TIMEOUT_S", "7200"))
POLL_INTERVAL_S = int(os.environ.get("SHOWCASE_QUICK_POLL_S", "30"))


def _get(base: str, path: str) -> dict:
    req = urllib.request.Request(f"{base}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _post(base: str, path: str) -> dict:
    req = urllib.request.Request(
        f"{base}{path}",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    base = (
        os.environ.get("AEGIS_API_URL")
        or (sys.argv[1] if len(sys.argv) > 1 else "")
    ).rstrip("/")
    if not base:
        print(
            "Usage: AEGIS_API_URL=https://... smoke_prod_showcase_quick.py",
            file=sys.stderr,
        )
        return 2

    t0 = time.time()
    print("POST", f"{base}/v1/showcase/runs/quick")
    try:
        session = _post(base, "/v1/showcase/runs/quick")
    except urllib.error.HTTPError as exc:
        print("HTTP error:", exc.code, exc.read().decode(errors="replace")[:2000], file=sys.stderr)
        return 1
    except Exception as exc:
        print("Start failed:", exc, file=sys.stderr)
        return 1

    session_id = session.get("session_id")
    if not session_id:
        print("FAIL: missing session_id", file=sys.stderr)
        return 1
    print("session_id:", session_id)

    terminal = {"needs_approval", "successful", "failed", "cancelled", "rejected"}
    last_stage = ""
    while time.time() - t0 < DEFAULT_TIMEOUT_S:
        try:
            session = _get(base, f"/v1/showcase/runs/{session_id}")
        except Exception as exc:
            print("poll error:", exc, file=sys.stderr)
            time.sleep(POLL_INTERVAL_S)
            continue

        status = session.get("status", "")
        diag = session.get("diagnostics") or {}
        stage = diag.get("stage", "")
        if stage != last_stage:
            elapsed = time.time() - t0
            print(
                f"[{elapsed:.0f}s] status={status} stage={stage} "
                f"cases={diag.get('completed_cases', 0)}/{diag.get('total_cases', 0)}"
            )
            last_stage = stage

        if status in terminal:
            elapsed = time.time() - t0
            print(f"finished in {elapsed:.1f}s status={status}")
            if status == "needs_approval":
                proposal = session.get("proposal") or {}
                candidate = proposal.get("candidate") or {}
                print("candidate_id:", candidate.get("candidate_id"))
                print("PASS: quick showcase reached needs_approval on prod")
                return 0
            err = diag.get("last_error") or {}
            print("FAIL:", err.get("code"), err.get("message"), file=sys.stderr)
            return 1

        time.sleep(POLL_INTERVAL_S)

    print(f"FAIL: timed out after {DEFAULT_TIMEOUT_S}s", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
