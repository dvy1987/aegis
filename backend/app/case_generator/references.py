"""denial_letter_references selection — public exemplar catalog + web-research cache.

Harvested from aplus/letter_references.py + aplus/web_references.py (merged, standalone).
Populates each case's ``denial_letter_references`` so judge J3 (grounding) has citable
sources. Catalog data lives in ``eval/references/`` (survives aplus deletion).
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import EVAL_DIR

CATALOG_PATH = EVAL_DIR / "references" / "denial-letter-realism-sources.json"
WEB_CACHE_PATH = EVAL_DIR / "references" / "web-research-cache-2026-06-02.json"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def load_web_cache() -> dict[str, Any]:
    with WEB_CACHE_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _by_id(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {e["ref_id"]: e for e in catalog.get("exemplars", [])}


def web_references_for_cell(cell: dict[str, str]) -> list[dict[str, str]]:
    """Web-sourced reference rows for the insurer × denial_type pool."""
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


def select_letter_references(
    *,
    insurer: str,
    denial_type: str,
    pattern_ids: list[str],
    cell: dict[str, str] | None = None,
    use_web_research: bool = True,
) -> list[dict[str, str]]:
    """Return 3–8 structured references attached to each synthetic case."""
    catalog = load_catalog()
    index = _by_id(catalog)
    chosen: list[str] = []
    for rid in catalog.get("insurer_affinity", {}).get(insurer, []):
        if rid not in chosen:
            chosen.append(rid)
    for rid in catalog.get("denial_type_affinity", {}).get(denial_type, []):
        if rid not in chosen:
            chosen.append(rid)
    for rid in ("cms-abd-model-2011", "erisa-29-cfr-2560-503-1"):
        if rid not in chosen:
            chosen.append(rid)
    if "missing_iro_notice" in pattern_ids and "aca-2719-29-cfr-147-136" not in chosen:
        chosen.append("aca-2719-29-cfr-147-136")
    if "step_therapy_vague_mcg" in pattern_ids and "kff-2023-consumer-survey" not in chosen:
        chosen.append("kff-2023-consumer-survey")
    if "circular_medical_necessity" in pattern_ids and "propublica-uncovered-2023" not in chosen:
        chosen.append("propublica-uncovered-2023")

    catalog_out: list[dict[str, str]] = []
    for rid in chosen[:6]:
        ex = index.get(rid)
        if not ex:
            continue
        borrowed = ex.get("borrowed_elements", [])
        relevance = (
            f"Calibrated P2 letter surface: {borrowed[0]}."
            if borrowed
            else "General denial-letter structure reference."
        )
        catalog_out.append(
            {
                "ref_id": rid,
                "title": ex["title"],
                "url": ex["url"],
                "source_type": ex["source_type"],
                "relevance": relevance,
            }
        )
    if use_web_research and cell:
        return merge_references(catalog_out, web_references_for_cell(cell))
    return catalog_out
