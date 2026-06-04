"""Statistical evaluator layer — AlphaEval's 3rd evaluator type.

The eval-pipeline skill mandates THREE evaluator types (deterministic + statistical +
LLM-judge); the generator had deterministic and LLM-judge but no statistical layer.

This module supplies deterministic, numeric, trend-trackable diversity metrics with NO
LLM call: trigram-Jaccard near-duplicate detection of a candidate case against (a) the
neighbours in the current run and (b) the WHOLE existing drafts corpus. The corpus check
is what lets the generator "diversify based on existing cases" — a case too close to one
already on disk is flagged for re-roll.

Complements (does not replace) the LLM ``diversity_delta`` critic: the LLM judges
*conceptual* near-duplication; this judges *lexical* overlap as a cheap, objective metric.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

# near-dup thresholds on max trigram Jaccard (0..1)
DUP_FAIL = 0.50   # >= this vs corpus/neighbour -> near-duplicate (gate fails -> re-roll)
DUP_WARN = 0.35   # >= this -> score 3 (acceptable but close); else 5


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _trigrams(text: str) -> frozenset[tuple[str, str, str]]:
    t = _tokens(text)
    return frozenset(zip(t, t[1:], t[2:]))


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _case_text(letter: str, clinical: str) -> str:
    return f"{letter}\n{clinical}"


@lru_cache(maxsize=8)
def _corpus_trigrams(drafts_dir: str, mtime_bucket: int) -> tuple[tuple[str, frozenset], ...]:
    """Cached trigram sets for every draft on disk. ``mtime_bucket`` invalidates the cache
    when the directory changes (pass int(dir mtime))."""
    out: list[tuple[str, frozenset]] = []
    d = Path(drafts_dir)
    if not d.exists():
        return tuple(out)
    for p in d.glob("case_*.json"):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        out.append((c.get("case_id", p.stem),
                    _trigrams(_case_text(c.get("denial_letter_text", ""),
                                         c.get("clinical_context", "")))))
    return tuple(out)


def corpus_trigrams(drafts_dir: Path) -> tuple[tuple[str, frozenset], ...]:
    d = Path(drafts_dir)
    bucket = int(d.stat().st_mtime) if d.exists() else 0
    return _corpus_trigrams(str(d), bucket)


def diversity_metrics(
    *,
    denial_letter_text: str,
    clinical_context: str,
    neighbour_texts: list[str],
    corpus: tuple[tuple[str, frozenset], ...],
    exclude_case_id: str | None = None,
) -> dict[str, Any]:
    """Return lexical-diversity metrics + nearest match for a candidate case."""
    cand = _trigrams(_case_text(denial_letter_text, clinical_context))

    nb = max((jaccard(cand, _trigrams(t)) for t in neighbour_texts), default=0.0)

    nearest_id, corp = "", 0.0
    for cid, tg in corpus:
        if cid == exclude_case_id:
            continue
        j = jaccard(cand, tg)
        if j > corp:
            corp, nearest_id = j, cid

    worst = max(nb, corp)
    return {
        "max_trigram_jaccard_neighbours": round(nb, 3),
        "max_trigram_jaccard_corpus": round(corp, 3),
        "nearest_corpus_case": nearest_id,
        "near_duplicate": bool(worst >= DUP_FAIL),
        "worst": round(worst, 3),
    }


def diversity_verdict(metrics: dict[str, Any]) -> dict[str, Any]:
    """Critic-style verdict for the statistical diversity layer (forced 1/3/5)."""
    worst = metrics.get("worst", 0.0)
    if worst >= DUP_FAIL:
        score = 1
    elif worst >= DUP_WARN:
        score = 3
    else:
        score = 5
    return {
        "dimension": "diversity_statistical",
        "reasoning": (
            f"Max trigram-Jaccard: corpus={metrics.get('max_trigram_jaccard_corpus')} "
            f"(nearest={metrics.get('nearest_corpus_case') or 'n/a'}), "
            f"neighbours={metrics.get('max_trigram_jaccard_neighbours')}. "
            f"Thresholds: warn>={DUP_WARN}, fail>={DUP_FAIL}."
        ),
        "score": score,
        "confidence": 1.0,
        "evidence_quotes": [],
        "improvement": (
            f"Too lexically similar to {metrics.get('nearest_corpus_case')}; "
            "diversify drug/trajectory/phrasing."
            if score == 1 else None
        ),
    }
