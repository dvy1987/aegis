"""Flaw-injection verifier — the generator↔judge alignment gate.

Harvested/expanded from ``aplus/flaws.py::verify_flaws_present`` (which covered 5
patterns) to all 24 patterns in ``eval/denial_patterns.json``.

WHY THIS EXISTS
---------------
The Part-A judges grade the student appeal against a *teacher packet* built by
``app.evals.part_a.teacher_packet.build_teacher_grading_packet``. That packet derives
``expected_appeal_vectors`` from each case's ``denial_pattern_sources`` (matched against
``denial_patterns.json``) and hands them to judge **J6 (appeal-vector capture)**. J6 then
checks whether the appeal attacked those vectors — but the student only ever sees
``denial_letter_text`` + ``clinical_context``.

So every flaw named in ``denial_pattern_sources`` MUST be genuinely *discoverable* in the
student-visible prose, or J6 expects something the student cannot find. This module is the
deterministic gate that enforces that contract at generation time.

Each pattern check returns one of:
  - ``"present"``    : a concrete textual hook exists (student can attack it)
  - ``"absent"``     : not inferable from the prose -> generation must revise/re-inject
  - ``"needs_llm"``  : semantic; defer to the LLM flaw-verifier critic

It also exposes ``format_pattern_sources`` so the generator emits ``denial_pattern_sources``
in the exact ``"{pattern_id}: {source}"`` shape the teacher packet parses.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

Status = Literal["present", "absent", "needs_llm"]


# --- teacher-packet-parseable source strings ---------------------------------

def format_pattern_sources(patterns: list[dict[str, Any]]) -> list[str]:
    """Return ['{id}: {source}', ...] — the format teacher_packet._pattern_matches_source
    keys off (it splits on the first ':' and matches the id)."""
    out: list[str] = []
    for p in patterns:
        pid = p.get("id")
        if not pid:
            continue
        src = p.get("source") or "published utilization-management research"
        out.append(f"{pid}: {src}")
    return out


# --- helpers -----------------------------------------------------------------

def _ts_delta_minutes(sub_ts: str | None, den_ts: str | None) -> float | None:
    if not sub_ts or not den_ts:
        return None
    try:
        a = datetime.fromisoformat(sub_ts.replace("Z", "+00:00"))
        b = datetime.fromisoformat(den_ts.replace("Z", "+00:00"))
        return (b - a).total_seconds() / 60.0
    except ValueError:
        return None


_PROSE_FAST_REVIEW = re.compile(
    r"\b\d{1,2}:\d{2}\b|within (?:\d+ |a few )?(?:minute|hour)|minutes? of receipt"
    r"|same[- ]day|on the (?:same )?date the request was received"
    r"|completed (?:on )?the (?:same )?(?:day|date)",
    re.I,
)
_EXTERNAL_REVIEW = re.compile(r"external review|independent review|\biro\b|independent review organization", re.I)
_ERISA = re.compile(r"erisa|29 u\.?s\.?c|1133|civil action|right to bring", re.I)
_COST_LIABILITY = re.compile(r"financial responsibility|member (?:cost|liability)|you (?:may )?be responsible|cost-?sharing|amount you owe", re.I)
_REVIEWER_CRED = re.compile(r"\bM\.?D\.?\b|board[- ]certified|medical license|\bDO\b|specialty:|, (?:Internal Medicine|Cardiology|Oncology|Psychiatry|Neurology)", re.I)
_REVIEWER_NAMED = re.compile(r"Dr\.\s+[A-Z]\.?\s*[A-Z][a-z]+|Medical Director", re.I)


# --- per-pattern checks ------------------------------------------------------
# Each returns Status from (letter_low, clinical_low, ctx)

def _ctx_get(ctx: dict[str, Any], key: str, default=None):
    return ctx.get(key, default)


def _chk_step_therapy_vague_mcg(l, c, ctx):
    return "present" if ("mcg" in l or "milliman" in l or "interqual" in l) and "edition" not in l else "absent"

def _chk_missing_erisa(l, c, ctx):
    # flaw present == disclosure ABSENT
    return "absent" if _ERISA.search(l) else "present"

def _chk_missing_cost_liability(l, c, ctx):
    return "absent" if _COST_LIABILITY.search(l) else "present"

def _chk_missing_iro(l, c, ctx):
    return "absent" if _EXTERNAL_REVIEW.search(l) else "present"

def _chk_timeline_violation(l, c, ctx):
    d = _ts_delta_minutes(ctx.get("sub_ts"), ctx.get("den_ts"))
    if d is not None and d > 30 * 24 * 60:  # > 30 days
        return "present"
    if re.search(r"\b(4[5-9]|[5-9]\d|\d{3})\s*(?:calendar )?days?\b", l):
        return "present"
    return "needs_llm"

def _chk_wrong_appeals_contact(l, c, ctx):
    return "present" if re.search(r"appeals?\s+(?:unit|department|contact)|p\.?o\.?\s*box|\bfax\b", l) else "absent"

def _chk_circular(l, c, ctx):
    if re.search(r"not medically necessary because.*medical necessity|does not meet.*necessity criteria because.*not medically necessary", l):
        return "present"
    return "needs_llm"

def _chk_incorrect_demo_guideline(l, c, ctx):
    return "present" if re.search(r"pediatric|geriatric|ages?\s*\d|adolescent criteria|age[- ]band", l) else "needs_llm"

def _chk_ignored_physician(l, c, ctx):
    boiler = re.search(r"regardless of information previously sent|standard criteria apply|did not include sufficient detail|does not (?:discuss|reflect)", l)
    has_evidence = bool(re.search(r"\d|mg|score|failed|trial", c))
    if boiler and has_evidence:
        return "present"
    return "needs_llm"

def _chk_superseded_guideline(l, c, ctx):
    yrs = [int(y) for y in re.findall(r"\b(20[01]\d|202[0-3])\b", l)]
    if any(y <= 2022 for y in yrs):
        return "present"
    return "needs_llm" if re.search(r"prior[- ]edition|outdated|superseded", l) else "absent"

def _chk_contraindication(l, c, ctx):
    return "present" if re.search(r"contraindicat|adverse reaction|intoleran|allerg", c) else "needs_llm"

def _chk_non_specialist_reviewer(l, c, ctx):
    # flaw present when a reviewer is named WITHOUT a relevant specialty/credential
    if _REVIEWER_NAMED.search(l) and not _REVIEWER_CRED.search(l):
        return "present"
    return "needs_llm"

def _chk_mhpaea(l, c, ctx):
    spec = (ctx.get("specialty") or "").lower()
    return "present" if spec == "behavioral_health" and re.search(r"parity|visit limit|step therapy|level of care|mhpaea", l) else "needs_llm"

def _chk_experimental(l, c, ctx):
    return "present" if re.search(r"experimental|investigational|unproven|not.*evidence-based", l) else "absent"

def _chk_wrong_benefit_category(l, c, ctx):
    return "present" if "benefit category" in l else "absent"

def _chk_plan_exclusion_state(l, c, ctx):
    ok = "plan exclusion" in l or ("state" in l and "mandate" in l)
    return "present" if ok else "absent"

def _chk_unreasonable_deadline(l, c, ctx):
    return "present" if re.search(r"within (?:24|48|72)\s*hours|within [1-5]\s*(?:business )?days|no extensions", l) else "absent"

def _chk_appeal_closed_withdrawn(l, c, ctx):
    return "present" if "withdrawn" in l else "absent"

def _chk_p2p_verbal(l, c, ctx):
    return "present" if re.search(r"verbal timeframe|verbally|by phone only|not confirmed in this letter", l) else "absent"

def _chk_algo_time_delta(l, c, ctx):
    d = _ts_delta_minutes(ctx.get("sub_ts"), ctx.get("den_ts"))
    ts_ok = d is not None and 1 <= d <= 5
    prose_ok = bool(_PROSE_FAST_REVIEW.search(ctx.get("letter_raw", "")))
    if ts_ok and prose_ok:
        return "present"            # judge-visible AND student-visible
    return "absent"                # either timestamps wrong or turnaround invisible in prose

def _chk_algo_boilerplate(l, c, ctx):
    return "present" if "[redacted]" in l or "the requested service." in l else "needs_llm"

def _chk_algo_reviewer_no_cred(l, c, ctx):
    # flaw present when NO reviewer identity/credentials are recorded, or explicitly automated
    if "automated" in l and "no individual reviewer" in l:
        return "present"
    return "present" if not _REVIEWER_NAMED.search(l) and not _REVIEWER_CRED.search(l) else "needs_llm"


_CHECKS = {
    "step_therapy_vague_mcg": _chk_step_therapy_vague_mcg,
    "missing_erisa_disclosures": _chk_missing_erisa,
    "missing_cost_liability": _chk_missing_cost_liability,
    "missing_iro_notice": _chk_missing_iro,
    "timeline_violation": _chk_timeline_violation,
    "wrong_appeals_contact": _chk_wrong_appeals_contact,
    "circular_medical_necessity": _chk_circular,
    "incorrect_demographic_guideline": _chk_incorrect_demo_guideline,
    "ignored_physician_letter": _chk_ignored_physician,
    "superseded_guideline": _chk_superseded_guideline,
    "contraindication_to_step_therapy": _chk_contraindication,
    "non_specialist_reviewer": _chk_non_specialist_reviewer,
    "mhpaea_visit_limit_asymmetry": _chk_mhpaea,
    "mhpaea_step_therapy_asymmetry": _chk_mhpaea,
    "mhpaea_level_of_care_asymmetry": _chk_mhpaea,
    "experimental_despite_fda_approval": _chk_experimental,
    "wrong_benefit_category": _chk_wrong_benefit_category,
    "plan_exclusion_overrides_state_mandate": _chk_plan_exclusion_state,
    "unreasonable_documentation_deadline": _chk_unreasonable_deadline,
    "appeal_closed_as_withdrawn": _chk_appeal_closed_withdrawn,
    "peer_to_peer_window_verbal_only": _chk_p2p_verbal,
    "algo_time_delta": _chk_algo_time_delta,
    "algo_boilerplate_fingerprint": _chk_algo_boilerplate,
    "algo_reviewer_no_credentials": _chk_algo_reviewer_no_cred,
}


def verify_flaws(
    *,
    denial_letter_text: str,
    clinical_context: str,
    pattern_ids: list[str],
    submission_timestamp: str | None = None,
    denial_timestamp: str | None = None,
    specialty: str | None = None,
    plan_funding_type: str | None = None,
) -> dict[str, Any]:
    """Verify each intended flaw is discoverable in student-visible text.

    Returns {present:[], absent:[], needs_llm:[], by_pattern:{id:status}}.
    ``absent`` is the gate signal — those flaws must be re-injected before the case is
    judge-aligned.
    """
    l = denial_letter_text.lower()
    c = clinical_context.lower()
    ctx = {
        "sub_ts": submission_timestamp,
        "den_ts": denial_timestamp,
        "specialty": specialty,
        "plan_funding_type": plan_funding_type,
        "letter_raw": denial_letter_text,
    }
    by_pattern: dict[str, Status] = {}
    for pid in pattern_ids:
        check = _CHECKS.get(pid)
        by_pattern[pid] = check(l, c, ctx) if check else "needs_llm"

    return {
        "by_pattern": by_pattern,
        "present": [p for p, s in by_pattern.items() if s == "present"],
        "absent": [p for p, s in by_pattern.items() if s == "absent"],
        "needs_llm": [p for p, s in by_pattern.items() if s == "needs_llm"],
        "aligned": all(s != "absent" for s in by_pattern.values()),
    }
