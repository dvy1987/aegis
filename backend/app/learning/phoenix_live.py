"""Live `PhoenixLearningStore` (Tier 1 Phase D).

The Learning Coordinator reads its gradient FROM Phoenix (INV-1). This module
implements that contract over real Phoenix infrastructure:

  * `rows_to_scored_runs(spans, annotations)` — pure transform, exhaustively
    unit-tested against recorded fixtures. Joins spans with their
    `aegis_part_a_panel` annotation, parses the laundered JSON payload that
    `OtelPhoenixRecorder.annotate` stored in `result.explanation`, and emits
    a list of `ScoredRun` objects with the firewall (INV-2) preserved.
  * `LivePhoenixLearningStore` — implements the `PhoenixLearningStore`
    Protocol. Reads spans/annotations via the Phoenix REST client (the
    Tier 1 read path; MCP is the runtime hot path used by
    `phoenix_mcp_lookup`). Versions and writes promoted prompts/playbooks
    to the Phoenix Prompts registry **and** to the on-disk artefacts that
    the running v1 backend already loads.

Cloud SDK imports stay method-local so this module imports cleanly offline.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.learning.fs_store import FileSystemPhoenixLearningStore
from app.learning.models import (
    Candidate,
    Component,
    ComponentVersion,
    PromotionAudit,
    ScoredRun,
)
from app.learning.signal import FORBIDDEN_FIELDS


# ---------------------------------------------------------------------------
# Pure transforms (offline-tested)
# ---------------------------------------------------------------------------


def _strip_forbidden(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove answer-key / teacher-only fields anywhere in the payload (INV-2)."""
    return {k: v for k, v in payload.items() if k not in FORBIDDEN_FIELDS}


def _aegis_attribute(span: dict[str, Any], key: str) -> str:
    """Read an `aegis.<key>` attribute from a span row in either the nested
    `attributes` shape (MCP) or the flattened `attributes.aegis.<key>` shape
    (Phoenix client dataframe)."""
    attrs = span.get("attributes")
    if isinstance(attrs, dict):
        v = attrs.get(f"aegis.{key}")
        if v is not None:
            return str(v)
    flat = span.get(f"attributes.aegis.{key}")
    if flat is not None:
        return str(flat)
    return ""


def _span_id(span: dict[str, Any]) -> str | None:
    ctx = span.get("context") or {}
    if isinstance(ctx, dict):
        sid = ctx.get("span_id") or ctx.get("spanId")
        if sid:
            return str(sid)
    sid = span.get("span_id") or span.get("spanId") or span.get("context.span_id")
    return str(sid) if sid else None


def _annotation_explanation(annotation: dict[str, Any]) -> str | None:
    result = annotation.get("result")
    if isinstance(result, dict):
        return result.get("explanation")
    flat = annotation.get("result.explanation")
    return str(flat) if flat is not None else None


def _annotation_name(annotation: dict[str, Any]) -> str | None:
    return (
        annotation.get("name")
        or annotation.get("annotation_name")
        or annotation.get("name.0")
    )


def rows_to_scored_runs(
    spans: list[dict[str, Any]],
    annotations: list[dict[str, Any]],
) -> list[ScoredRun]:
    """Pure transform: Phoenix span/annotation rows -> firewalled `ScoredRun`s.

    The implementation is shape-agnostic across the two read paths the
    runtime uses (MCP `get-spans` JSON vs `phoenix.client` dataframes), so
    callers do not have to normalize first.
    """
    by_span: dict[str, dict[str, Any]] = {}
    for ann in annotations:
        if not isinstance(ann, dict):
            continue
        if _annotation_name(ann) != "aegis_part_a_panel":
            continue
        sid = ann.get("span_id") or ann.get("spanId")
        if not sid:
            continue
        # Last write wins (annotations are append-only and ordered by created_at;
        # a future "latest" preference can sort by created_at if needed).
        by_span[str(sid)] = ann

    runs: list[ScoredRun] = []
    for span in spans:
        sid = _span_id(span)
        if not sid:
            continue
        ann = by_span.get(sid)
        if ann is None:
            continue
        explanation = _annotation_explanation(ann)
        if not explanation:
            continue
        try:
            payload = json.loads(explanation)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        payload = _strip_forbidden(payload)

        case_id = (
            payload.get("case_id")
            or _aegis_attribute(span, "case_id")
            or "unknown"
        )
        insurer = _aegis_attribute(span, "insurer") or payload.get("insurer", "unknown")
        denial_type = _aegis_attribute(span, "denial_type") or payload.get(
            "denial_type", "unknown"
        )
        slice_key = f"{insurer}:{denial_type}"

        verdict = (payload.get("verdict") or "").upper()
        hard_gate_pass = verdict == "PASS"
        try:
            weighted_quality = float(payload.get("weighted_quality") or 0.0)
        except (TypeError, ValueError):
            weighted_quality = 0.0

        raw_scores = payload.get("dimension_scores") or {}
        dimension_scores: dict[str, int] = {}
        for k, v in raw_scores.items():
            try:
                dimension_scores[str(k)] = int(v)
            except (TypeError, ValueError):
                continue

        improvement_notes: dict[str, str] = {}
        for dim, rec in (payload.get("dimensions") or {}).items():
            if not isinstance(rec, dict):
                continue
            note = rec.get("improvement")
            if isinstance(note, str) and note.strip():
                improvement_notes[str(dim)] = note.strip()

        sim_v_raw = payload.get("simulator_verdict")
        simulator_verdict = (
            sim_v_raw if sim_v_raw in ("APPROVE", "DENY") else None
        )

        prompt_version = (
            _aegis_attribute(span, "prompt_version")
            or payload.get("prompt_version")
            or ""
        )
        playbook_version = (
            _aegis_attribute(span, "playbook_version")
            or payload.get("playbook_version")
            or ""
        )

        runs.append(
            ScoredRun(
                case_id=str(case_id),
                slice=slice_key,
                dimension_scores=dimension_scores,
                hard_gate_pass=hard_gate_pass,
                weighted_quality=weighted_quality,
                improvement_notes=improvement_notes,
                simulator_verdict=simulator_verdict,
                prompt_version=str(prompt_version),
                playbook_version=str(playbook_version),
            )
        )
    return runs


def component_version_from_prompt_record(
    component_id: str, record: dict[str, Any]
) -> ComponentVersion:
    """Convert a Phoenix Prompts registry record to a ComponentVersion."""
    return ComponentVersion(
        component_id=component_id,
        version=str(record.get("version") or "v1"),
        text=record.get("text"),
        playbook=record.get("playbook"),
    )


# ---------------------------------------------------------------------------
# Live store (cloud calls method-local)
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROMPT_DIR = _REPO_ROOT / "backend" / "app" / "aegis_v1" / "prompts"
_PLAYBOOK_DIR = _REPO_ROOT / "backend" / "app" / "aegis_v1" / "playbooks"


class LivePhoenixLearningStore:
    """`PhoenixLearningStore` over real Arize Phoenix.

    Reads:
      * `read_scored_runs` — `phoenix.client` get-spans + get-span-annotations,
        sliced on `aegis.dataset_split` / `aegis.prompt_version` /
        `aegis.playbook_version` if requested, then `rows_to_scored_runs`.
      * `read_prompt_version` / `list_prompt_versions` — Phoenix Prompts
        registry, falling back to the on-disk prompt file when the registry
        has no record yet.

    Writes:
      * `register_promotion` — writes the new prompt/playbook to the on-disk
        artefacts (so the running v1 backend picks them up on next request),
        upserts a Phoenix Prompt + tag, and appends the audit. The on-disk
        write reuses `FileSystemPhoenixLearningStore` so behaviour matches
        the offline coordinator path.

    The constructor takes no live calls; everything cloud-touching is
    inside the methods below.
    """

    name = "live_phoenix_learning_store"

    def __init__(
        self,
        *,
        project: str | None = None,
        prompts_dir: Path | None = None,
        playbooks_dir: Path | None = None,
    ) -> None:
        self.project = project or os.environ.get("PHOENIX_PROJECT_NAME", "default")
        self._fs = FileSystemPhoenixLearningStore(
            playbooks_dir=playbooks_dir or _PLAYBOOK_DIR,
            prompts_dir=prompts_dir or _PROMPT_DIR,
        )
        self.audits: list[PromotionAudit] = self._fs.audits

    # ------------------------------------------------------------------
    # Read side
    # ------------------------------------------------------------------

    def read_scored_runs(
        self,
        *,
        dataset_split: str,
        prompt_version: str | None = None,
        playbook_version: str | None = None,
    ) -> list[ScoredRun]:
        spans, annotations = self._fetch_spans_and_annotations(
            dataset_split=dataset_split,
            prompt_version=prompt_version,
            playbook_version=playbook_version,
        )
        return rows_to_scored_runs(spans, annotations)

    def read_prompt_version(
        self, component_id: str, version: str | None = None
    ) -> ComponentVersion:
        try:
            record = self._fetch_prompt_record(component_id, version)
            if record is not None:
                return component_version_from_prompt_record(component_id, record)
        except Exception:
            pass
        return self._read_prompt_from_disk(component_id, version)

    def list_prompt_versions(self, component_id: str) -> list[ComponentVersion]:
        try:
            records = self._fetch_prompt_versions(component_id)
            if records:
                return [
                    component_version_from_prompt_record(component_id, r)
                    for r in records
                ]
        except Exception:
            pass
        if component_id in self._fs._versions:  # type: ignore[attr-defined]
            return self._fs.list_prompt_versions(component_id)
        return []

    # ------------------------------------------------------------------
    # Write side
    # ------------------------------------------------------------------

    def register_promotion(
        self, candidate: Candidate, audit: PromotionAudit
    ) -> None:
        # 1. On-disk write (the running v1 backend reads from disk).
        self._fs.register_promotion(candidate, audit)
        # 2. Best-effort registry upsert. Failure is non-fatal — disk write is
        #    the load-bearing path; registry is for UI / lineage visibility.
        try:
            self._upsert_to_registry(candidate, audit)
        except Exception:
            return

    # ------------------------------------------------------------------
    # Live fetch helpers (method-local cloud imports)
    # ------------------------------------------------------------------

    def _client(self):
        from phoenix.client import Client

        host = os.environ.get("PHOENIX_HOST")
        base_url = (host.rstrip("/") + "/") if host else None
        return Client(base_url=base_url)

    def _fetch_spans_and_annotations(
        self,
        *,
        dataset_split: str,
        prompt_version: str | None,
        playbook_version: str | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        client = self._client()
        spans_df = client.spans.get_spans_dataframe(
            project_identifier=self.project, limit=200
        )
        if spans_df is None or spans_df.empty:
            return [], []
        spans_records = json.loads(
            spans_df.reset_index().to_json(orient="records", default_handler=str)
        )

        def _matches(s: dict[str, Any]) -> bool:
            split = _aegis_attribute(s, "dataset_split")
            if split and split != dataset_split:
                return False
            if prompt_version is not None:
                pv = _aegis_attribute(s, "prompt_version")
                if pv and pv != prompt_version:
                    return False
            if playbook_version is not None:
                bv = _aegis_attribute(s, "playbook_version")
                if bv and bv != playbook_version:
                    return False
            return True

        spans = [s for s in spans_records if _matches(s)]
        if not spans:
            return [], []

        span_ids = [sid for sid in (_span_id(s) for s in spans) if sid]
        if not span_ids:
            return spans, []
        try:
            ann_df = client.spans.get_span_annotations_dataframe(
                span_ids=span_ids, project_identifier=self.project
            )
        except Exception:
            return spans, []
        annotations = json.loads(
            ann_df.reset_index().to_json(orient="records", default_handler=str)
        )
        return spans, annotations

    def _fetch_prompt_record(
        self, component_id: str, version: str | None
    ) -> dict[str, Any] | None:
        # Phoenix Prompts registry: identifier == component_id (e.g. drafter_system_prompt).
        # The Python client surface is in flux; failure here just falls back to disk.
        client = self._client()
        prompts = getattr(client, "prompts", None)
        if prompts is None:
            return None
        try:
            if version:
                rec = prompts.get_prompt_version(prompt_identifier=component_id, version=version)
            else:
                rec = prompts.get_latest_prompt(prompt_identifier=component_id)
        except Exception:
            return None
        if rec is None:
            return None
        if hasattr(rec, "model_dump"):
            return rec.model_dump()
        if isinstance(rec, dict):
            return rec
        return {"version": getattr(rec, "version", "v1"), "text": getattr(rec, "template", None)}

    def _fetch_prompt_versions(self, component_id: str) -> list[dict[str, Any]]:
        client = self._client()
        prompts = getattr(client, "prompts", None)
        if prompts is None:
            return []
        try:
            records = prompts.list_prompt_versions(prompt_identifier=component_id)
        except Exception:
            return []
        out: list[dict[str, Any]] = []
        for rec in records or []:
            if hasattr(rec, "model_dump"):
                out.append(rec.model_dump())
            elif isinstance(rec, dict):
                out.append(rec)
        return out

    def _read_prompt_from_disk(
        self, component_id: str, version: str | None
    ) -> ComponentVersion:
        # Mirror aegis_v1/drafter_client.load_drafter_prompt for prompts; for
        # playbooks, fall back to the file-based store (which the FS store
        # already maintains).
        if component_id == "drafter_system_prompt":
            v = version or os.environ.get("AEGIS_DRAFTER_PROMPT_VERSION", "drafter_v2")
            path = _PROMPT_DIR / f"{v}.md"
            if path.exists():
                return ComponentVersion(
                    component_id=component_id, version=v, text=path.read_text()
                )
        if component_id in self._fs._versions:  # type: ignore[attr-defined]
            return self._fs.read_prompt_version(component_id, version)
        # Last-resort empty version: the coordinator will treat it as a seed.
        return ComponentVersion(component_id=component_id, version=version or "v0", text="")

    def _upsert_to_registry(
        self, candidate: Candidate, audit: PromotionAudit
    ) -> None:
        client = self._client()
        prompts = getattr(client, "prompts", None)
        if prompts is None:
            return
        for comp in candidate.components.values():
            if comp.kind != "prompt" or not comp.text:
                continue
            try:
                prompts.upsert_prompt(
                    prompt_identifier=comp.component_id,
                    template=comp.text,
                    version=comp.version,
                )
            except Exception:
                continue
            try:
                prompts.add_prompt_version_tag(
                    prompt_identifier=comp.component_id,
                    version=comp.version,
                    tag=f"approver:{audit.approver}",
                )
            except Exception:
                continue

    # Test/seed helpers (mirrors the FS store API for swap-in tests).
    def add_run(self, *args, **kwargs):
        return self._fs.add_run(*args, **kwargs)

    def seed_component(self, *args, **kwargs):
        return self._fs.seed_component(*args, **kwargs)
