#!/usr/bin/env python3
"""Smoke-test showcase approve flow on deployed aegis-v1-api (Phase 5).

Requires a session in ``needs_approval`` (or pass SHOWCASE_SESSION_ID), then:
  POST /v1/showcase/runs/{id}/approve → poll until ``successful`` or ``failed``.

Optionally start a fresh quick run when START_QUICK=1 (60–120+ minutes).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

POLL_INTERVAL_S = int(os.environ.get("SHOWCASE_APPROVE_POLL_S", "30"))
TIMEOUT_S = int(os.environ.get("SHOWCASE_APPROVE_TIMEOUT_S", "1800"))
APPROVER = os.environ.get("SHOWCASE_APPROVER", "prod_smoke")


def _get(base: str, path: str) -> dict:
    req = urllib.request.Request(f"{base}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _post(base: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _poll_until_needs_approval(base: str, session_id: str, t0: float) -> dict:
    while time.time() - t0 < TIMEOUT_S:
        session = _get(base, f"/v1/showcase/runs/{session_id}")
        status = session.get("status", "")
        if status == "needs_approval":
            return session
        if status in {"failed", "cancelled", "rejected"}:
            raise RuntimeError(f"session ended before approval: {status}")
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"timed out waiting for needs_approval ({TIMEOUT_S}s)")


def main() -> int:
    base = (
        os.environ.get("AEGIS_API_URL")
        or (sys.argv[1] if len(sys.argv) > 1 else "")
    ).rstrip("/")
    if not base:
        print(
            "Usage: AEGIS_API_URL=https://... [SHOWCASE_SESSION_ID=...] smoke_prod_showcase_approve.py",
            file=sys.stderr,
        )
        return 2

    t0 = time.time()
    session_id = os.environ.get("SHOWCASE_SESSION_ID", "").strip()

    if not session_id:
        if os.environ.get("START_QUICK", "").lower() in {"1", "true", "yes"}:
            print("POST", f"{base}/v1/showcase/runs/quick")
            started = _post(base, "/v1/showcase/runs/quick")
            session_id = started["session_id"]
            print("session_id:", session_id)
            _poll_until_needs_approval(base, session_id, t0)
        else:
            print(
                "Set SHOWCASE_SESSION_ID to a needs_approval session, "
                "or START_QUICK=1 to run the full quick flow first.",
                file=sys.stderr,
            )
            return 2

    session = _get(base, f"/v1/showcase/runs/{session_id}")
    if session.get("status") != "needs_approval":
        if os.environ.get("WAIT_FOR_APPROVAL", "").lower() in {"1", "true", "yes"}:
            session = _poll_until_needs_approval(base, session_id, t0)
        else:
            print(
                f"FAIL: session status is {session.get('status')!r}, expected needs_approval",
                file=sys.stderr,
            )
            return 1

    print("POST", f"{base}/v1/showcase/runs/{session_id}/approve")
    _post(base, f"/v1/showcase/runs/{session_id}/approve", {"approver": APPROVER})

    while time.time() - t0 < TIMEOUT_S:
        session = _get(base, f"/v1/showcase/runs/{session_id}")
        status = session.get("status", "")
        diag = session.get("diagnostics") or {}
        if status in {"successful", "failed"}:
            elapsed = time.time() - t0
            print(f"finished in {elapsed:.1f}s status={status}")
            if status == "successful":
                cp = session.get("checkpoint") or {}
                print("promotion_done:", cp.get("promotion_done"))
                print("post_measure_done:", cp.get("post_measure_done"))
                print("regression_detected:", session.get("regression_detected"))
                print("PASS: showcase approve flow on prod")
                return 0
            err = diag.get("last_error") or {}
            print("FAIL:", err.get("code"), err.get("message"), file=sys.stderr)
            return 1
        time.sleep(POLL_INTERVAL_S)

    print(f"FAIL: timed out after {TIMEOUT_S}s", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
