"""Live Phoenix-MCP fetch helper used by `phoenix_mcp_lookup`.

Reads laundered span annotations for a slice (insurer, denial_type) from a
Phoenix project and returns a list of trace dicts shaped like the laundered
payload that `_summarize_traces` consumes.

Read path order (per PM directive: "MCP first; Phoenix client only as fallback"):
  1. ``@arizeai/phoenix-mcp`` (npx, stdio). Calls ``get-spans`` filtered by
     project, then ``get-span-annotations`` for those span ids; merges by id.
  2. ``phoenix.client.Client`` REST fallback if MCP fails.

The function never raises out to the caller — on any failure it returns ``[]``
which the lookup turns into a ``cold_start`` summary, preserving graceful
degradation. Cloud/SDK imports are method-local so the offline test suite and
``import app.aegis_v1.tools`` stay clean.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any


WORKING_AUTH_RECIPE = """\
# Working auth recipe verified against Arize Phoenix Cloud (project=default).
#   PHOENIX_API_KEY=<key>
#   PHOENIX_HOST=https://app.phoenix.arize.com/s/<workspace>
#   PHOENIX_CLIENT_HEADERS=api_key=$PHOENIX_API_KEY     # auto-derived if absent
#   PHOENIX_PROJECT_NAME=default                         # pinned in main_v1.py
"""


def fetch_slice_traces(
    *,
    insurer: str,
    denial_type: str,
    project: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return up to ``limit`` laundered trace dicts for the slice. Empty on any
    failure path."""
    proj = project or os.environ.get("PHOENIX_PROJECT_NAME", "default")
    try:
        traces = _fetch_via_mcp(insurer, denial_type, proj, limit)
        if traces:
            return traces
    except Exception:
        traces = []
    try:
        return _fetch_via_client(insurer, denial_type, proj, limit)
    except Exception:
        return []


def _decode_text(content: Any) -> str:
    if isinstance(content, list) and content:
        return getattr(content[0], "text", str(content[0]))
    return str(content)


def _slice_filter(span_attrs: dict[str, Any], *, insurer: str, denial_type: str) -> bool:
    """True iff this span's tagged metadata matches the requested slice."""
    try:
        attr_insurer = (span_attrs.get("aegis.insurer") or "").strip().lower()
        attr_denial = (span_attrs.get("aegis.denial_type") or "").strip().lower()
    except AttributeError:
        return False
    return attr_insurer == insurer.strip().lower() and attr_denial == denial_type.strip().lower()


def _join_spans_with_annotations(
    spans: list[dict[str, Any]], annotations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Pair each span with its `aegis_part_a_panel` annotation (if any) and
    return the parsed laundered payload, augmented with span metadata. Spans
    without a matching annotation are dropped (they have no signal)."""
    by_span: dict[str, list[dict[str, Any]]] = {}
    for ann in annotations:
        if not isinstance(ann, dict):
            continue
        if ann.get("name") != "aegis_part_a_panel":
            continue
        sid = ann.get("span_id") or ann.get("spanId")
        if sid:
            by_span.setdefault(sid, []).append(ann)

    out: list[dict[str, Any]] = []
    for span in spans:
        ctx = span.get("context") or {}
        sid = ctx.get("span_id") or span.get("span_id") or span.get("spanId")
        anns = by_span.get(sid) if sid else None
        if not anns:
            continue
        explanation = (anns[0].get("result") or {}).get("explanation") or ""
        try:
            payload = json.loads(explanation)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        attrs = span.get("attributes") or {}
        payload.setdefault("aegis_attributes", attrs)
        out.append(payload)
    return out


async def _async_fetch_via_mcp(
    insurer: str, denial_type: str, project: str, limit: int
) -> list[dict[str, Any]]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = os.environ.copy()
    env["PHOENIX_PROJECT"] = project
    if "PHOENIX_API_KEY" in env and "PHOENIX_CLIENT_HEADERS" not in env:
        env["PHOENIX_CLIENT_HEADERS"] = f"api_key={env['PHOENIX_API_KEY']}"
    params = StdioServerParameters(
        command="npx", args=["-y", "@arizeai/phoenix-mcp"], env=env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            spans_res = await session.call_tool(
                "get-spans",
                arguments={"projectIdentifier": project, "limit": max(limit * 4, 50)},
            )
            spans_payload = json.loads(_decode_text(spans_res.content))
            spans = spans_payload.get("spans", []) if isinstance(spans_payload, dict) else []
            spans = [
                s for s in spans
                if _slice_filter(s.get("attributes") or {}, insurer=insurer, denial_type=denial_type)
            ]
            spans = spans[:limit]
            if not spans:
                return []

            span_ids: list[str] = []
            for s in spans:
                ctx = s.get("context") or {}
                sid = ctx.get("span_id") or s.get("span_id") or s.get("spanId")
                if sid:
                    span_ids.append(sid)
            if not span_ids:
                return []
            ann_res = await session.call_tool(
                "get-span-annotations", arguments={"span_ids": span_ids}
            )
            ann_payload = json.loads(_decode_text(ann_res.content))
            annotations = (
                ann_payload.get("annotations", [])
                if isinstance(ann_payload, dict)
                else (ann_payload if isinstance(ann_payload, list) else [])
            )
            return _join_spans_with_annotations(spans, annotations)


def _fetch_via_mcp(
    insurer: str, denial_type: str, project: str, limit: int
) -> list[dict[str, Any]]:
    return asyncio.run(_async_fetch_via_mcp(insurer, denial_type, project, limit))


def _fetch_via_client(
    insurer: str, denial_type: str, project: str, limit: int
) -> list[dict[str, Any]]:
    from phoenix.client import Client

    host = os.environ.get("PHOENIX_HOST")
    base_url = (host.rstrip("/") + "/") if host else None
    client = Client(base_url=base_url)
    spans_df = client.spans.get_spans_dataframe(
        project_identifier=project, limit=max(limit * 4, 50)
    )
    spans = json.loads(
        spans_df.reset_index().to_json(orient="records", default_handler=str)
    )
    spans = [
        s for s in spans
        if _slice_filter(
            {k: v for k, v in s.items() if k.startswith("attributes.aegis.")},
            insurer=insurer,
            denial_type=denial_type,
        )
        or _slice_filter(s.get("attributes") or {}, insurer=insurer, denial_type=denial_type)
    ]
    spans = spans[:limit]
    if not spans:
        return []
    span_ids = []
    for s in spans:
        sid = s.get("context.span_id") or s.get("span_id")
        if sid:
            span_ids.append(sid)
    if not span_ids:
        return []
    ann_df = client.spans.get_span_annotations_dataframe(
        span_ids=span_ids, project_identifier=project
    )
    annotations = json.loads(
        ann_df.reset_index().to_json(orient="records", default_handler=str)
    )
    for ann in annotations:
        if "annotation_name" in ann and "name" not in ann:
            ann["name"] = ann["annotation_name"]
        if "result.explanation" in ann:
            ann.setdefault("result", {})["explanation"] = ann["result.explanation"]
    return _join_spans_with_annotations(spans, annotations)
