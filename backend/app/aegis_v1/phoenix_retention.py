"""Automatic Phoenix span retention for Cloud free-tier caps.

Phoenix Cloud enforces limits on **span** count. When a project exceeds the
configured threshold, delete the oldest **traces** (which removes all child
spans) until the span budget is back under the limit.

Designed for mid-GEPA floods:

* ``ensure_phoenix_span_budget()`` runs **synchronously before every Phoenix
  write** so exports do not hit the hard cap and stall the run.
* Active showcase ``dataset_split`` values are protected so seed training
  annotations GEPA still reads are not pruned mid-session.
* The newest ``protect_newest`` spans are never targeted (count-based floor).
* No age-based floor — same-day GEPA runs are the common case.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_prune_lock = threading.Lock()
_protected_splits_lock = threading.Lock()
_protected_dataset_splits: set[str] = set()

DEFAULT_THRESHOLD = 20_000
DEFAULT_BATCH = 5_000
DEFAULT_PROTECT_NEWEST = 15_000
DEFAULT_MAX_ROUNDS_PER_ENSURE = 8


@dataclass(frozen=True)
class PruneResult:
    checked: bool
    pruned: bool
    reason: str
    span_count_before: int | None = None
    deleted_traces: int = 0
    dry_run: bool = False


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def phoenix_prune_enabled() -> bool:
    raw = os.environ.get("AEGIS_PHOENIX_PRUNE_ENABLED", "").strip().lower()
    if raw in {"0", "false", "no"}:
        return False
    if raw in {"1", "true", "yes"}:
        return True
    return bool(os.environ.get("PHOENIX_HOST"))


def phoenix_prune_dry_run() -> bool:
    return os.environ.get("AEGIS_PHOENIX_PRUNE_DRY_RUN", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def set_protected_dataset_splits(splits: set[str] | list[str]) -> None:
    with _protected_splits_lock:
        global _protected_dataset_splits
        _protected_dataset_splits = {s for s in splits if s}


def clear_protected_dataset_splits() -> None:
    set_protected_dataset_splits(set())


def get_protected_dataset_splits() -> set[str]:
    with _protected_splits_lock:
        return set(_protected_dataset_splits)


def register_showcase_session_splits(session_id: str, train_split: str) -> None:
    """Protect GEPA training + measure splits for an active showcase session."""
    set_protected_dataset_splits(
        {
            train_split,
            f"showcase_pre_measure_{session_id}",
            f"showcase_training_pre_measure_{session_id}",
            f"showcase_post_measure_{session_id}",
        }
    )


def _phoenix_client():
    from phoenix.client import Client

    host = os.environ.get("PHOENIX_HOST")
    base_url = (host.rstrip("/") + "/") if host else None
    return Client(base_url=base_url)


def _project_traces_url(project_identifier: str) -> str:
    from phoenix.client.utils.encode_path_param import encode_path_param

    return f"v1/projects/{encode_path_param(project_identifier)}/traces"


def _project_spans_url(project_identifier: str) -> str:
    from phoenix.client.utils.encode_path_param import encode_path_param

    return f"v1/projects/{encode_path_param(project_identifier)}/spans"


def _trace_identifier(trace: dict[str, Any]) -> str | None:
    for key in ("trace_id", "id"):
        value = trace.get(key)
        if value:
            return str(value)
    return None


def _span_dataset_split(span: dict[str, Any]) -> str:
    attrs = span.get("attributes")
    if isinstance(attrs, dict):
        value = attrs.get("aegis.dataset_split")
        if value is not None:
            return str(value)
    return ""


def count_project_spans(
    client: Any,
    *,
    project_identifier: str,
    early_exit_above: int | None = None,
) -> int:
    """Count spans via paginated list API; stop early once above threshold."""
    total = 0
    cursor: str | None = None
    page_size = 100
    spans_url = _project_spans_url(project_identifier)
    while True:
        params: dict[str, Any] = {"limit": page_size}
        if cursor:
            params["cursor"] = cursor
        response = client._client.get(
            url=spans_url,
            params=params,
            headers={"accept": "application/json"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        page = list(payload.get("data") or [])
        total += len(page)
        if early_exit_above is not None and total > early_exit_above:
            return total
        cursor = payload.get("next_cursor")
        if not cursor or not page:
            return total


def _list_oldest_traces(
    client: Any,
    *,
    project_identifier: str,
    limit: int,
) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    cursor: str | None = None
    page_size = min(100, limit)
    traces_url = _project_traces_url(project_identifier)
    while len(traces) < limit:
        remaining = limit - len(traces)
        params: dict[str, Any] = {
            "limit": min(page_size, remaining),
            "sort": "start_time",
            "order": "asc",
        }
        if cursor:
            params["cursor"] = cursor
        response = client._client.get(
            url=traces_url,
            params=params,
            headers={"accept": "application/json"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        page = list(payload.get("data") or [])
        if not page:
            break
        traces.extend(page)
        cursor = payload.get("next_cursor")
        if not cursor:
            break
    return traces[:limit]


def _trace_is_protected(
    client: Any,
    *,
    project_identifier: str,
    trace_id: str,
    protected_splits: set[str],
) -> bool:
    if not protected_splits:
        return False
    try:
        spans = client.spans.get_spans(
            project_identifier=project_identifier,
            trace_ids=[trace_id],
            limit=25,
            timeout=30,
        )
    except Exception:
        # Conservative: if we cannot inspect attributes, keep the trace.
        return True
    for span in spans:
        if _span_dataset_split(span) in protected_splits:
            return True
    return False


def _delete_trace(client: Any, trace_identifier: str) -> bool:
    from phoenix.client.utils.encode_path_param import encode_path_param

    response = client._client.delete(
        url=f"v1/traces/{encode_path_param(trace_identifier)}",
        timeout=60,
    )
    if response.status_code == 404:
        return False
    response.raise_for_status()
    return response.status_code == 204


def prune_phoenix_spans_if_needed(
    *,
    project_name: str | None = None,
    threshold: int | None = None,
    batch: int | None = None,
    protect_newest: int | None = None,
    dry_run: bool | None = None,
) -> PruneResult:
    """Delete oldest unprotected traces until span count is back under threshold."""
    if not phoenix_prune_enabled():
        return PruneResult(checked=False, pruned=False, reason="disabled")

    project = project_name or os.environ.get("PHOENIX_PROJECT_NAME", "default")
    threshold = threshold if threshold is not None else _env_int(
        "AEGIS_PHOENIX_PRUNE_THRESHOLD", DEFAULT_THRESHOLD
    )
    batch = batch if batch is not None else _env_int("AEGIS_PHOENIX_PRUNE_BATCH", DEFAULT_BATCH)
    protect_newest = protect_newest if protect_newest is not None else _env_int(
        "AEGIS_PHOENIX_PRUNE_PROTECT_NEWEST", DEFAULT_PROTECT_NEWEST
    )
    dry_run = phoenix_prune_dry_run() if dry_run is None else dry_run
    protected_splits = get_protected_dataset_splits()

    if batch <= 0 or threshold <= 0:
        return PruneResult(checked=False, pruned=False, reason="invalid_config")
    if protect_newest >= threshold:
        return PruneResult(checked=False, pruned=False, reason="invalid_protect_newest")

    try:
        client = _phoenix_client()
    except Exception:
        logger.warning("phoenix prune: client init failed", exc_info=True)
        return PruneResult(checked=False, pruned=False, reason="client_init_failed")

    try:
        span_count = count_project_spans(
            client, project_identifier=project, early_exit_above=threshold
        )
    except Exception:
        logger.warning("phoenix prune: span count failed project=%s", project, exc_info=True)
        return PruneResult(checked=False, pruned=False, reason="count_failed")

    if span_count <= threshold:
        return PruneResult(
            checked=True,
            pruned=False,
            reason="under_threshold",
            span_count_before=span_count,
            dry_run=dry_run,
        )

    if span_count - protect_newest <= 0:
        return PruneResult(
            checked=True,
            pruned=False,
            reason="protect_newest_floor",
            span_count_before=span_count,
            dry_run=dry_run,
        )

    max_traces = min(200, max(20, batch // 25))
    deleted_traces = 0
    skipped_protected = 0
    try:
        candidates = _list_oldest_traces(
            client,
            project_identifier=project,
            limit=max_traces * 3,
        )
    except Exception:
        logger.warning("phoenix prune: list oldest traces failed", exc_info=True)
        return PruneResult(
            checked=True,
            pruned=False,
            reason="list_failed",
            span_count_before=span_count,
            dry_run=dry_run,
        )

    for trace in candidates:
        if deleted_traces >= max_traces:
            break
        ident = _trace_identifier(trace)
        if not ident:
            continue
        if _trace_is_protected(
            client,
            project_identifier=project,
            trace_id=ident,
            protected_splits=protected_splits,
        ):
            skipped_protected += 1
            continue
        if dry_run:
            deleted_traces += 1
            continue
        try:
            if _delete_trace(client, ident):
                deleted_traces += 1
        except Exception:
            logger.warning(
                "phoenix prune: delete failed trace_id=%s", ident, exc_info=True
            )

    if deleted_traces == 0:
        reason = "only_protected_remaining" if skipped_protected else "no_eligible_traces"
        return PruneResult(
            checked=True,
            pruned=False,
            reason=reason,
            span_count_before=span_count,
            dry_run=dry_run,
        )

    span_after: int | None = None
    if not dry_run:
        try:
            span_after = count_project_spans(
                client,
                project_identifier=project,
                early_exit_above=threshold,
            )
        except Exception:
            span_after = None

    logger.info(
        "phoenix span prune project=%s spans_before=%s spans_after=%s "
        "deleted_traces=%s skipped_protected=%s dry_run=%s max_traces=%s",
        project,
        span_count,
        span_after,
        deleted_traces,
        skipped_protected,
        dry_run,
        max_traces,
    )
    return PruneResult(
        checked=True,
        pruned=not dry_run,
        reason="dry_run" if dry_run else "pruned",
        span_count_before=span_count,
        deleted_traces=deleted_traces,
        dry_run=dry_run,
    )


def ensure_phoenix_span_budget(*, project_name: str | None = None) -> None:
    """Synchronous auto-prune before Phoenix writes — prevents hard-cap write failures."""
    if not phoenix_prune_enabled():
        return

    max_rounds = _env_int(
        "AEGIS_PHOENIX_PRUNE_MAX_ROUNDS_PER_ENSURE", DEFAULT_MAX_ROUNDS_PER_ENSURE
    )
    with _prune_lock:
        for _ in range(max_rounds):
            result = prune_phoenix_spans_if_needed(project_name=project_name)
            if result.reason in {"disabled", "under_threshold"}:
                return
            if not result.pruned:
                if result.reason in {
                    "only_protected_remaining",
                    "protect_newest_floor",
                    "no_eligible_traces",
                }:
                    logger.warning(
                        "phoenix span budget still tight: %s (spans=%s)",
                        result.reason,
                        result.span_count_before,
                    )
                return


# Back-compat alias for older hook name.
def maybe_prune_phoenix_traces(*, project_name: str | None = None) -> None:
    ensure_phoenix_span_budget(project_name=project_name)


# Back-compat alias.
prune_phoenix_traces_if_needed = prune_phoenix_spans_if_needed


def count_project_traces(
    client: Any,
    *,
    project_identifier: str,
    early_exit_above: int | None = None,
) -> int:
    """Deprecated: Phoenix cap is on spans. Kept for older tests/callers."""
    return count_project_spans(
        client,
        project_identifier=project_identifier,
        early_exit_above=early_exit_above,
    )
