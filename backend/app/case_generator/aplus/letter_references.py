"""Load public denial-letter exemplar catalog and pick refs per case."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.case_generator.config import EVAL_DIR

from .web_references import merge_references, web_references_for_cell

CATALOG_PATH = EVAL_DIR / "references" / "denial-letter-realism-sources.json"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    with CATALOG_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _by_id(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {e["ref_id"]: e for e in catalog.get("exemplars", [])}


def select_letter_references(
    *,
    insurer: str,
    denial_type: str,
    pattern_ids: list[str],
    cell: dict[str, str] | None = None,
    use_web_research: bool = False,
) -> list[dict[str, str]]:
    """Return 3–6 structured references attached to each synthetic case."""
    catalog = load_catalog()
    index = _by_id(catalog)
    chosen: list[str] = []
    for rid in catalog.get("insurer_affinity", {}).get(insurer, []):
        if rid not in chosen:
            chosen.append(rid)
    for rid in catalog.get("denial_type_affinity", {}).get(denial_type, []):
        if rid not in chosen:
            chosen.append(rid)
    # Always anchor to federal notice template + ERISA content rules
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
        web_refs = web_references_for_cell(cell)
        return merge_references(catalog_out, web_refs)
    return catalog_out
