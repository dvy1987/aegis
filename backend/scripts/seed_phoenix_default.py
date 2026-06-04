"""One-shot script: seed real spans + laundered annotations into Phoenix project
'default' so the Tier 1 transforms have real fixtures to parse.

Run from backend/:
    env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/seed_phoenix_default.py

Picks three diverse cases across (insurer, denial_type) slices, runs each through
``run_evaluated_case`` with the live ``OtelPhoenixRecorder`` against project
``default``, and prints the resulting trace refs. Uses the offline heuristic
judge (no Vertex required) so the script is creds-light: only ``PHOENIX_API_KEY``
and ``PHOENIX_HOST`` are required.

Cases written by this seed are valid test artefacts in their own right — they
exercise the full Student → recorder → panel → annotation path.
"""
from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

# Mirror main_v1.py's IPv4-first patch so phoenix.client() doesn't hang on
# macOS IPv6 resolution (Google + Phoenix endpoints).
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_first_getaddrinfo

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_phoenix_env() -> None:
    if "PHOENIX_API_KEY" not in os.environ:
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    if "PHOENIX_API_KEY" not in os.environ:
        sys.exit("PHOENIX_API_KEY missing; populate .env first.")
    os.environ["PHOENIX_PROJECT_NAME"] = "default"
    if "PHOENIX_CLIENT_HEADERS" not in os.environ:
        os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={os.environ['PHOENIX_API_KEY']}"
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")


def main() -> None:
    _ensure_phoenix_env()

    from app.aegis_v1.drafter_client import StubDrafterClient
    from app.app_utils.telemetry import setup_telemetry
    from app.evals.part_a.evaluated_run import run_evaluated_case
    from app.evals.part_a.recorder import OtelPhoenixRecorder

    setup_telemetry()

    seeds = [
        REPO_ROOT / "eval" / "cases" / "drafts" / "case_01_cigna_mednec.json",
        REPO_ROOT / "eval" / "cases" / "drafts" / "case_02_cigna_priorauth.json",
        REPO_ROOT / "eval" / "cases" / "drafts" / "case_03_aetna_mednec.json",
    ]

    recorder = OtelPhoenixRecorder(project_name="default")
    drafter = StubDrafterClient()
    refs: list[tuple[str, str]] = []
    for path in seeds:
        case_obj = json.loads(path.read_text())
        case_obj["dataset_split"] = "benchmark_train"
        run = run_evaluated_case(
            case_obj,
            recorder=recorder,
            drafter_client=drafter,
            run_simulator=False,
        )
        refs.append((case_obj["case_id"], run.trace_ref))
        print(f"  seeded {case_obj['case_id']:30s} -> span_id={run.trace_ref}")

    print("\nSeeded trace refs:")
    for cid, ref in refs:
        print(f"  {cid}: {ref}")
    print("\nFlushing OTEL spans (waiting for batch export)...")

    from opentelemetry import trace as otel_trace

    provider = otel_trace.get_tracer_provider()
    if hasattr(provider, "force_flush"):
        provider.force_flush(timeout_millis=10_000)
    print("Done.")


if __name__ == "__main__":
    main()
