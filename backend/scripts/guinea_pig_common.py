"""Shared env, IPv4 patch, and Gemini cost tracking for guinea-pig CLI scripts."""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPO_ROOT / "eval" / "GUINEA-PIG-RUNS"

_PRICE_PER_M = {
    "gemini-3.1-pro-preview": {"input": 1.25, "output": 5.00},
    "gemini-3.5-flash": {"input": 0.15, "output": 0.60},
    "default": {"input": 1.25, "output": 5.00},
}

_orig_getaddrinfo = socket.getaddrinfo


def ipv4_first_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


def apply_ipv4_patch() -> None:
    socket.getaddrinfo = ipv4_first_getaddrinfo


def load_env(*, require_phoenix: bool = False) -> None:
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    os.environ["PHOENIX_PROJECT_NAME"] = "default"
    if os.environ.get("PHOENIX_API_KEY") and "PHOENIX_CLIENT_HEADERS" not in os.environ:
        os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={os.environ['PHOENIX_API_KEY']}"
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
    if require_phoenix:
        if not os.environ.get("PHOENIX_API_KEY"):
            sys.exit("PHOENIX_API_KEY missing; populate .env first.")
        if not os.environ.get("PHOENIX_HOST"):
            sys.exit("PHOENIX_HOST missing; populate .env first (Phoenix Cloud API base URL).")
        if not os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"):
            sys.exit(
                "PHOENIX_COLLECTOR_ENDPOINT missing; populate .env first "
                "(OTEL trace export URL, usually …/v1/traces)."
            )


def ping_phoenix(*, project: str = "default") -> dict[str, Any]:
    """Verify Phoenix Cloud API + collector env before spending Gemini credits."""
    from phoenix.client import Client

    host = os.environ.get("PHOENIX_HOST")
    base_url = (host.rstrip("/") + "/") if host else None
    client = Client(base_url=base_url)
    spans_df = client.spans.get_spans_dataframe(project_identifier=project, limit=5)
    span_count = 0 if spans_df is None else int(len(spans_df))
    return {
        "ok": True,
        "project": project,
        "phoenix_host": host,
        "collector": os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"),
        "recent_span_rows": span_count,
    }


def setup_phoenix_telemetry() -> None:
    """Register OTEL → Phoenix Cloud (same as main_v1.py / seed_phoenix_default.py).

    Without this, ``run_evaluated_case`` spans never reach Phoenix, judge
    annotations have nothing to attach to, and GEPA returns ``no_learning_signal``.
    """
    from opentelemetry import trace
    from opentelemetry.trace import NoOpTracerProvider

    from app.app_utils.telemetry import setup_telemetry

    setup_telemetry()
    provider = trace.get_tracer_provider()
    if isinstance(provider, NoOpTracerProvider):
        sys.exit(
            "Phoenix telemetry failed to register (still NoOpTracerProvider). "
            "Check PHOENIX_API_KEY and PHOENIX_COLLECTOR_ENDPOINT in .env."
        )


def install_token_tracker() -> list[dict[str, Any]]:
    """Patch Gemini calls to record usage_metadata from every response."""
    import app.gemini_retry as gr

    records: list[dict[str, Any]] = []
    original = gr.generate_content_with_fallback

    def tracking_fallback(generate_content, *, model: str, fallback_model=None, **kwargs):
        response = original(
            generate_content,
            model=model,
            fallback_model=fallback_model,
            **kwargs,
        )
        usage = getattr(response, "usage_metadata", None)
        prompt_t = int(getattr(usage, "prompt_token_count", 0) or 0)
        output_t = int(getattr(usage, "candidates_token_count", 0) or 0)
        total_t = int(getattr(usage, "total_token_count", 0) or 0) or (prompt_t + output_t)
        records.append(
            {
                "model": model,
                "prompt_tokens": prompt_t,
                "output_tokens": output_t,
                "total_tokens": total_t,
            }
        )
        return response

    gr.generate_content_with_fallback = tracking_fallback
    return records


def estimate_cost_usd(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_model: dict[str, dict[str, int]] = {}
    for row in records:
        model = str(row.get("model") or "default")
        bucket = by_model.setdefault(
            model,
            {"calls": 0, "prompt_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
        bucket["calls"] += 1
        bucket["prompt_tokens"] += int(row.get("prompt_tokens") or 0)
        bucket["output_tokens"] += int(row.get("output_tokens") or 0)
        bucket["total_tokens"] += int(row.get("total_tokens") or 0)

    total_usd = 0.0
    model_costs: dict[str, Any] = {}
    for model, counts in by_model.items():
        rates = _PRICE_PER_M.get(model) or _PRICE_PER_M["default"]
        input_usd = counts["prompt_tokens"] / 1_000_000 * rates["input"]
        output_usd = counts["output_tokens"] / 1_000_000 * rates["output"]
        subtotal = round(input_usd + output_usd, 6)
        total_usd += subtotal
        model_costs[model] = {**counts, "estimated_usd": round(subtotal, 6)}

    return {
        "gemini_calls": len(records),
        "per_model": model_costs,
        "total_prompt_tokens": sum(r.get("prompt_tokens", 0) for r in records),
        "total_output_tokens": sum(r.get("output_tokens", 0) for r in records),
        "total_tokens": sum(r.get("total_tokens", 0) for r in records),
        "estimated_total_usd": round(total_usd, 4),
        "pricing_note": (
            "Partial estimate: tracks generate_content_with_fallback only; "
            "ADK agent calls are not included. Verify against GCP billing."
        ),
        "per_call": records,
    }
