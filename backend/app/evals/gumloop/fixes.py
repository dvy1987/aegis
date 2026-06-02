from __future__ import annotations

import re
from typing import Any, Iterable

from app.case_generator.aplus.letter_enhancements import enhance_denial_letter
from app.case_generator.aplus.text_metrics import fit_letter_word_budget, repair_denial_letter_artifacts


def _parse_pattern_ids(denial_pattern_sources: Iterable[str]) -> list[str]:
    ids: list[str] = []
    for s in denial_pattern_sources:
        if not s:
            continue
        ids.append(str(s).split(":", 1)[0].strip())
    return [x for x in ids if x]


def _remove_external_review_language(letter: str) -> str:
    # Conservative: remove sentences mentioning external review / IRO.
    lines = re.split(r"(?<=[\.\n])\s+", letter)
    kept: list[str] = []
    for chunk in lines:
        c_l = chunk.lower()
        if any(m in c_l for m in ["external review", "independent external review", "independent review organization", "iro"]):
            continue
        kept.append(chunk)
    return " ".join(kept).replace("  ", " ").strip()


def _remove_cost_liability_language(letter: str) -> str:
    lines = re.split(r"(?<=[\.\n])\s+", letter)
    kept: list[str] = []
    for chunk in lines:
        c_l = chunk.lower()
        if any(m in c_l for m in ["financially responsible", "financial responsibility", "you may be billed", "balance bill"]):
            continue
        kept.append(chunk)
    return " ".join(kept).replace("  ", " ").strip()


def _strip_llm_tells(letter: str, clinical_context: str) -> tuple[str, str]:
    tell_repls = [
        (re.compile(r"\bIt is important to note that\s*", re.I), ""),
        (re.compile(r"\bI understand this may be frustrating\s*", re.I), ""),
        (re.compile(r"\bI hope this helps\.?\s*", re.I), ""),
        (re.compile(r"\bWith this in mind,?\s*", re.I), ""),
        (re.compile(r"\bBuilding on the above,?\s*", re.I), ""),
    ]
    for rx, repl in tell_repls:
        letter = rx.sub(repl, letter)
        clinical_context = rx.sub(repl, clinical_context)
    return letter.strip(), clinical_context.strip()


def apply_safe_fixes(case: dict[str, Any]) -> dict[str, Any]:
    """Apply safe, idempotent fixes aligned with Gumloop critics.

    - Preserves intended flaw patterns by removing content that would negate a "missing_*" flaw.
    - Strips obvious LLM-tell phrases.
    - Re-runs letter enhancement (claim-file / P2P blocks) if missing, then re-fits word budget.
    """
    denial = str(case.get("denial_letter_text") or "")
    ctx = str(case.get("clinical_context") or "")
    denial, ctx = _strip_llm_tells(denial, ctx)

    pattern_ids = _parse_pattern_ids(case.get("denial_pattern_sources") or [])

    # Enforce "missing_*" flaws by removing conflicting disclosures.
    if "missing_iro_notice" in pattern_ids:
        denial = _remove_external_review_language(denial)
    if "missing_cost_liability" in pattern_ids:
        denial = _remove_cost_liability_language(denial)

    # Ensure our standard realism blocks are present (claim file + P2P), unless explicitly forbidden by a pattern.
    # (No current pattern forbids claim-file/P2P.)
    insurer = str(case.get("insurer") or "")
    refs = case.get("denial_letter_references") or []
    try:
        denial = enhance_denial_letter(
            denial,
            insurer=insurer,
            denial_type=str(case.get("denial_type") or ""),
            denial_letter_references=refs,
            fit_budget=True,
        )
    except Exception:
        # Enhancement should be best-effort; never crash the offline pass.
        pass

    denial = fit_letter_word_budget(repair_denial_letter_artifacts(denial))

    case = dict(case)
    case["denial_letter_text"] = denial
    case["clinical_context"] = ctx
    return case

