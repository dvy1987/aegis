"""Track B (live thesis) smoke test.

Walks the live pipe one link at a time, prints a green/red line per link:
  L1  imports                — backend modules import cleanly
  L2  env                    — required env vars are set
  L3  vertex auth            — a minimal Gemini call returns text
  L4  phoenix tracing        — the call above produces a Phoenix span
  L5  outcome simulator      — the LLM judge step works

Exit 0 if all green; non-zero on first red. Designed to be run via:
    uv run --env-file ../.env python scripts/smoke_track_b.py
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Any


def _print(tag: str, link: str, msg: str = "") -> None:
    color = {"OK": "\033[32m", "FAIL": "\033[31m", "...": "\033[33m"}.get(tag, "")
    reset = "\033[0m"
    suffix = f" — {msg}" if msg else ""
    print(f"  [{color}{tag:^4}{reset}] {link}{suffix}", flush=True)


def link1_imports() -> bool:
    _print("...", "L1 imports")
    try:
        from app import main_v1  # noqa: F401
        from app.aegis_v1 import appeal_api, drafter_client, simulator_client  # noqa: F401
    except Exception as e:
        _print("FAIL", "L1 imports", f"{type(e).__name__}: {e}")
        traceback.print_exc()
        return False
    _print("OK", "L1 imports")
    return True


def link2_env() -> bool:
    _print("...", "L2 env")
    required = [
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "PHOENIX_API_KEY",
        "PHOENIX_COLLECTOR_ENDPOINT",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        _print("FAIL", "L2 env", f"missing: {', '.join(missing)}")
        return False
    _print("OK", "L2 env", f"project={os.environ['GOOGLE_CLOUD_PROJECT']}")
    return True


def link3_vertex_auth() -> tuple[bool, Any]:
    _print("...", "L3 vertex auth (Gemini call)")
    try:
        from google import genai

        client = genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        )
        t0 = time.time()
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with the single word: PONG",
        )
        elapsed = time.time() - t0
        text = (resp.text or "").strip()
        if "PONG" not in text.upper():
            _print("FAIL", "L3 vertex auth", f"unexpected reply: {text!r}")
            return False, None
        _print("OK", "L3 vertex auth", f"reply={text!r} in {elapsed:.2f}s")
        return True, client
    except Exception as e:
        _print("FAIL", "L3 vertex auth", f"{type(e).__name__}: {e}")
        traceback.print_exc()
        return False, None


def link4_phoenix_tracing() -> bool:
    _print("...", "L4 phoenix tracing (setup + second call latency)")
    try:
        os.environ["PHOENIX_PROJECT_NAME"] = "aegis-smoke"
        from app.app_utils.telemetry import setup_telemetry

        setup_telemetry()
        from google import genai

        client = genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        )
        t0 = time.time()
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with the single word: TRACE_OK",
        )
        elapsed = time.time() - t0
        text = (resp.text or "").strip()
        _print(
            "OK",
            "L4 phoenix tracing",
            f"call returned {text!r} in {elapsed:.2f}s (warm latency; trace in project=aegis-smoke)",
        )
        if elapsed > 10:
            _print("FAIL", "L4 phoenix tracing", f"warm latency {elapsed:.1f}s is too slow for live demo")
            return False
        return True
    except Exception as e:
        _print("FAIL", "L4 phoenix tracing", f"{type(e).__name__}: {e}")
        traceback.print_exc()
        return False


def link5_simulator() -> bool:
    _print("...", "L5 outcome simulator (LLM judge)")
    try:
        from app.aegis_v1.simulator_client import GeminiSimulatorClient

        client = GeminiSimulatorClient()
        case = {
            "case_id": "smoke_test",
            "insurer": "Aetna",
            "denial_type": "medical_necessity",
            "denial_reason": "Service not medically necessary",
            "appeal_letter": "Dear Aetna, the requested service is medically necessary per ACOG guidelines.",
        }
        result = client.assess(case)
        _print("OK", "L5 outcome simulator", f"assess returned {len(str(result))} chars")
        return True
    except Exception as e:
        _print("FAIL", "L5 outcome simulator", f"{type(e).__name__}: {e}")
        traceback.print_exc()
        return False


def main() -> int:
    print("Track B (live thesis) smoke test")
    print("=" * 60)

    if not link1_imports():
        return 1
    if not link2_env():
        return 1
    ok, _ = link3_vertex_auth()
    if not ok:
        return 1
    if not link4_phoenix_tracing():
        return 1
    if not link5_simulator():
        return 1

    print("=" * 60)
    print("\033[32mAll links green.\033[0m")
    print("Now safe to start backend (uv run uvicorn app.main_v1:app --port 8001)")
    print("and POST /v1/appeal end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
