"""Merge agent web-research cache into per-case denial_letter_references."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.case_generator.config import EVAL_DIR

WEB_CACHE_PATH = EVAL_DIR / "references" / "web-research-cache-2026-06-02.json"


@lru_cache(maxsize=1)
def load_web_cache() -> dict[str, Any]:
    with WEB_CACHE_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def web_references_for_cell(cell: dict[str, str]) -> list[dict[str, str]]:
    """Return web-sourced reference rows for insurer × denial_type pool."""
    cache = load_web_cache()
    sources = cache.get("sources", {})
    pool_key = f"{cell['insurer']}|{cell['denial_type']}"
    researched_at = cache.get("researched_at", "unknown")
    out: list[dict[str, str]] = []
    for sid in cache.get("pools", {}).get(pool_key, []):
        src = sources.get(sid)
        if not src:
            continue
        specialty = cell.get("specialty", "general").replace("_", " ")
        sub = cell.get("sub_tactic", "").replace("_", " ")
        out.append(
            {
                "ref_id": sid,
                "title": src["title"],
                "url": src["url"],
                "source_type": src["source_type"],
                "relevance": (
                    f"Web research ({researched_at}): {src['search_query']}. "
                    f"Calibrated to this synthetic {specialty} case ({sub})."
                ),
            }
        )
    return out


def merge_references(
    catalog_refs: list[dict[str, str]],
    web_refs: list[dict[str, str]],
    *,
    max_items: int = 8,
) -> list[dict[str, str]]:
    seen_urls: set[str] = set()
    merged: list[dict[str, str]] = []
    for ref in web_refs + catalog_refs:
        url = ref.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        merged.append(ref)
        if len(merged) >= max_items:
            break
    return merged
