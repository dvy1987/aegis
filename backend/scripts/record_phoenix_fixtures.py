"""Fetch real spans + span-annotations + traces from Phoenix project 'default'
and save them as offline test fixtures under backend/tests/fixtures/phoenix/.

Tries the MCP path first (`@arizeai/phoenix-mcp`) per the PM's "MCP first"
preference, then falls back to ``phoenix.client.Client`` if MCP fails. The
recorded JSON pins the real column/field names that the offline transforms
(`_summarize_traces`, `rows_to_scored_runs`) parse against.

Run from backend/:
    env UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/record_phoenix_fixtures.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "backend" / "tests" / "fixtures" / "phoenix"


def _ensure_env() -> None:
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    if "PHOENIX_API_KEY" not in os.environ:
        sys.exit("PHOENIX_API_KEY missing; populate .env first.")
    os.environ["PHOENIX_PROJECT_NAME"] = "default"
    os.environ["PHOENIX_PROJECT"] = "default"
    if "PHOENIX_CLIENT_HEADERS" not in os.environ:
        os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={os.environ['PHOENIX_API_KEY']}"


def _decode_text(content) -> str:
    if isinstance(content, list) and content:
        return getattr(content[0], "text", str(content[0]))
    return str(content)


async def _fetch_via_mcp() -> dict[str, list]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = os.environ.copy()
    params = StdioServerParameters(
        command="npx", args=["-y", "@arizeai/phoenix-mcp"], env=env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            spans_res = await session.call_tool(
                "get-spans", arguments={"projectIdentifier": "default", "limit": 50}
            )
            traces_res = await session.call_tool(
                "list-traces",
                arguments={"projectIdentifier": "default", "limit": 50},
            )
            spans_payload = json.loads(_decode_text(spans_res.content))
            traces_payload = json.loads(_decode_text(traces_res.content))

            span_ids: list[str] = []
            for s in spans_payload.get("spans", []):
                ctx = s.get("context") or {}
                sid = ctx.get("span_id") or s.get("span_id") or s.get("spanId")
                if sid:
                    span_ids.append(sid)
            annotations_payload: list = []
            if span_ids:
                ann_res = await session.call_tool(
                    "get-span-annotations",
                    arguments={"span_ids": span_ids[:50]},
                )
                ann_text = _decode_text(ann_res.content)
                try:
                    annotations_payload = json.loads(ann_text)
                except json.JSONDecodeError:
                    annotations_payload = [{"raw": ann_text}]
            return {
                "spans": spans_payload.get("spans", []),
                "traces": traces_payload,
                "annotations": annotations_payload,
            }


def _fetch_via_client() -> dict[str, list]:
    from phoenix.client import Client

    client = Client()
    spans_df = client.spans.get_spans_dataframe(project_identifier="default", limit=50)
    spans = json.loads(spans_df.reset_index().to_json(orient="records", default_handler=str))
    span_ids = [
        s.get("context.span_id") or s.get("span_id") for s in spans
    ]
    span_ids = [sid for sid in span_ids if sid]
    annotations: list = []
    if span_ids:
        try:
            ann_df = client.spans.get_span_annotations_dataframe(span_ids=span_ids)
            annotations = json.loads(
                ann_df.reset_index().to_json(orient="records", default_handler=str)
            )
        except Exception as exc:
            annotations = [{"error": f"client annotations fetch failed: {exc!r}"}]
    return {"spans": spans, "traces": [], "annotations": annotations}


def main() -> None:
    _ensure_env()
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    payload: dict[str, list] = {}
    used = "mcp"
    try:
        payload = asyncio.run(_fetch_via_mcp())
        if not payload.get("spans"):
            raise RuntimeError("MCP returned 0 spans; falling back to client")
    except Exception as exc:
        print(f"MCP fetch failed ({exc!r}); falling back to phoenix.client", flush=True)
        used = "client"
        payload = _fetch_via_client()

    spans_path = FIXTURE_DIR / "spans_sample.json"
    traces_path = FIXTURE_DIR / "traces_sample.json"
    annotations_path = FIXTURE_DIR / "annotations_sample.json"
    spans_path.write_text(json.dumps(payload.get("spans", []), indent=2, default=str))
    traces_path.write_text(json.dumps(payload.get("traces", []), indent=2, default=str))
    annotations_path.write_text(
        json.dumps(payload.get("annotations", []), indent=2, default=str)
    )

    n_spans = len(payload.get("spans", []))
    n_anns = len(payload.get("annotations", []))
    print(f"\nFixtures recorded via {used}:")
    print(f"  spans       : {n_spans:4d}  -> {spans_path.relative_to(REPO_ROOT)}")
    print(f"  annotations : {n_anns:4d}  -> {annotations_path.relative_to(REPO_ROOT)}")
    print(f"  traces      :        -> {traces_path.relative_to(REPO_ROOT)}")
    if n_spans == 0:
        print("\nWARNING: 0 spans recorded. Re-run scripts/seed_phoenix_default.py "
              "and wait ~10s for batch export before re-running this script.")


if __name__ == "__main__":
    main()
