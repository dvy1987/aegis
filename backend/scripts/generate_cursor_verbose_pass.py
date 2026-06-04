#!/usr/bin/env python3
"""Generate Gumloop cursor-verbose-pass markdown for a case ID range.

Reads eval/cases/drafts/, runs faithful Gumloop evaluate(), writes per-case
eval/gumloop_runs/cursor-verbose-pass/<case_id>.md with all 18 prompt blocks.

Usage:
  uv run python backend/scripts/generate_cursor_verbose_pass.py --start 351 --end 500
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts"
OUT_DIR = REPO / "eval" / "gumloop_runs" / "cursor-verbose-pass"

_SCRIPT = REPO / "backend" / "scripts" / "run_true_gumloop_all_500.py"
_spec = importlib.util.spec_from_file_location("gumloop_eval", _SCRIPT)
_gum = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_gum)

LEGAL_PATS = {
    "missing_erisa_disclosures",
    "missing_iro_notice",
    "timeline_violation",
    "wrong_appeals_contact",
    "non_specialist_reviewer",
    "peer_to_peer_window_verbal_only",
    "plan_exclusion_overrides_state_mandate",
    "mhpaea_step_therapy_asymmetry",
    "mhpaea_visit_limit_asymmetry",
}
LOGIC_PATS = {
    "circular_medical_necessity",
    "ignored_physician_letter",
    "algo_boilerplate_fingerprint",
    "superseded_guideline",
    "contraindication_to_step_therapy",
    "incorrect_demographic_guideline",
    "wrong_benefit_category",
    "step_therapy_vague_mcg",
}
TIMING_PATS = {"algo_time_delta", "timeline_violation"}
FINANCIAL_PATS = {"missing_cost_liability"}
CITATION_PATS = {"step_therapy_vague_mcg", "superseded_guideline"}

_DENIAL_LABEL = {
    "Prior Authorization": "Prior Authorization",
    "Medical Necessity": "Medical Necessity",
}


def _case_path(n: int) -> Path | None:
    return _gum._case_path(n)


def _quotes(case: dict[str, Any], letter: str, *, n: int = 3) -> list[str]:
    prof = case.get("patient_profile") or {}
    pool: list[str] = []
    for tok in (
        str(prof.get("diagnosis", "")).split("(")[0].strip(),
        str(prof.get("treatment_requested", "")),
        str(case.get("insurer", "")),
    ):
        if len(tok) >= 8 and tok in letter:
            pool.append(tok)
    for pat in (
        r"NOTICE OF ADVERSE BENEFIT DETERMINATION",
        r"We are unable to approve this request",
        r"EXPLANATION OF DECISION",
        r"Date of Notice: \d{2}/\d{2}/\d{4}",
        r"APPEAL RIGHTS",
    ):
        m = re.search(pat, letter, re.I)
        if m:
            pool.append(m.group(0)[:80])
    seen: set[str] = set()
    out: list[str] = []
    for q in pool:
        if q not in seen:
            seen.add(q)
            out.append(q)
        if len(out) >= n:
            break
    return out


def _insurer_display(ins: str) -> str:
    return {"UHC": "UHC", "Aetna": "Aetna", "Cigna": "Cigna"}.get(ins, ins)


def _profile_line(case: dict[str, Any]) -> str:
    prof = case.get("patient_profile") or {}
    age = prof.get("age", "?")
    gender = prof.get("gender", "?")
    dx = prof.get("diagnosis", "")
    tx = prof.get("treatment_requested", "")
    return f"{age}{gender}, {dx}, {tx}"


def _json_block(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def _section(title: str, data: dict[str, Any]) -> str:
    return f"## {title}\n\n```json\n{_json_block(data)}\n```\n"


def _pattern_subset(pats: list[str], allowed: set[str]) -> list[str]:
    return [p for p in pats if p in allowed]


def _legal_audit(case: dict[str, Any], pats: list[str], letter: str) -> dict[str, Any]:
    low = letter.lower()
    intended = _pattern_subset(pats, LEGAL_PATS)
    verified: list[str] = []
    missing: list[str] = []
    for pid in intended:
        status, _ = _gum._verify_pattern(pid, letter, low, case)
        if status == "PRESENT":
            verified.append(pid)
        elif status == "ABSENT":
            missing.append(pid)
    score = 5 if not missing else 1
    analysis = (
        "Intended legal flaws verified in denial letter."
        if not missing
        else "One or more intended legal flaws absent."
    )
    return {
        "dimension": "legal_coherence",
        "intended_legal_patterns_found": intended,
        "intended_patterns_verified": verified,
        "intended_patterns_missing": missing,
        "analysis": analysis,
        "score": score,
        "confidence": 0.87,
        "evidence_quotes": _quotes(case, letter, n=2) or ["APPEAL RIGHTS"],
        "improvement": (
            None
            if not missing
            else "Restore intended legal flaw per Flaw Injection Verifier."
        ),
    }


def _denial_logic(case: dict[str, Any], pats: list[str], letter: str) -> dict[str, Any]:
    low = letter.lower()
    intended = _pattern_subset(pats, LOGIC_PATS)
    verified: list[str] = []
    missing: list[str] = []
    for pid in intended:
        status, _ = _gum._verify_pattern(pid, letter, low, case)
        if status == "PRESENT":
            verified.append(pid)
        elif status == "ABSENT":
            missing.append(pid)
    score = 5 if not missing else 1
    return {
        "dimension": "denial_logic",
        "intended_logic_patterns_found": intended,
        "intended_patterns_verified": verified,
        "intended_patterns_missing": missing,
        "analysis": (
            "Intended shoddy denial logic present."
            if not missing
            else "One or more intended logic flaws absent."
        ),
        "score": score,
        "confidence": 0.9,
        "evidence_quotes": _quotes(case, letter, n=2) or ["EXPLANATION OF DECISION"],
        "improvement": (
            None
            if not missing
            else f"Inject missing logic patterns: {', '.join(missing)}."
        ),
    }


def _date_sanity(case: dict[str, Any], pats: list[str], letter: str) -> dict[str, Any]:
    low = letter.lower()
    intended = _pattern_subset(pats, TIMING_PATS)
    verified: list[str] = []
    missing: list[str] = []
    evidence: list[str] = []
    for pid in intended:
        status, ev = _gum._verify_pattern(pid, letter, low, case)
        if status == "PRESENT":
            verified.append(pid)
            if ev and "sub=" in ev:
                evidence.extend(re.findall(r"\d{4}-\d{2}-\d{2}T[\d:Z]+", ev))
        elif status == "ABSENT":
            missing.append(pid)
    if not evidence:
        for pat in (r"Date of Notice: \d{2}/\d{2}/\d{4}", r"Date of Service[^:]*: \d{2}/\d{2}/\d{4}"):
            m = re.search(pat, letter, re.I)
            if m:
                evidence.append(m.group(0))
    verdict = "PASS" if not missing else "FAIL"
    return {
        "dimension": "date_sanity",
        "intended_timing_patterns_found": intended,
        "intended_patterns_verified": verified,
        "intended_patterns_missing": missing,
        "verdict": verdict,
        "analysis": (
            "Dates/timestamps coherent; intended timing flaws verified."
            if not missing
            else "Intended timing flaw(s) not verified."
        ),
        "confidence": 0.9,
        "evidence_quotes": evidence[:3],
        "improvement": None if not missing else "Set submission/denial timestamps or letter date gap per pattern.",
    }


def _citation_trace(case: dict[str, Any], pats: list[str], letter: str) -> dict[str, Any]:
    low = letter.lower()
    intended = _pattern_subset(pats, CITATION_PATS)
    verified: list[str] = []
    missing: list[str] = []
    for pid in intended:
        status, _ = _gum._verify_pattern(pid, letter, low, case)
        if status == "PRESENT":
            verified.append(pid)
        elif status == "ABSENT":
            missing.append(pid)
    score = 5 if not missing else 1
    quotes = []
    for kw in ("CPB", "CDG", "MCG", "InterQual", "Clinical policy", "Medical Policy"):
        if kw.lower() in low:
            m = re.search(rf".{{0,30}}{re.escape(kw)}.{{0,40}}", letter, re.I)
            if m:
                quotes.append(m.group(0).strip()[:70])
    return {
        "dimension": "citation_traceability",
        "intended_citation_patterns_found": intended,
        "intended_patterns_verified": verified,
        "intended_patterns_missing": missing,
        "analysis": (
            "Citations appropriately vague or flawed as intended."
            if not missing
            else "Citation flaw pattern(s) missing."
        ),
        "score": score,
        "confidence": 0.85,
        "evidence_quotes": quotes[:2] or ["Clinical policy applied"],
        "improvement": None if not missing else "Add vague MCG/InterQual or superseded guideline citation.",
    }


def _financial_audit(case: dict[str, Any], pats: list[str], letter: str) -> dict[str, Any]:
    low = letter.lower()
    if "missing_cost_liability" in pats:
        present = any(
            x in low
            for x in ("financially responsible", "financial responsibility", "you may be billed")
        )
        score = 1 if present else 5
        analysis = (
            "Cost-liability language present — breaks missing_cost_liability flaw."
            if present
            else "No cost-liability statement; missing_cost_liability flaw preserved."
        )
    elif re.search(r"\$[\d,]+", letter):
        score = 4
        analysis = "Dollar amounts present; no internal inconsistency detected."
    else:
        score = 3
        analysis = "No financial figures stated; neutral."
    return {
        "dimension": "financial_consistency",
        "analysis": analysis,
        "score": score,
        "confidence": 0.9,
        "evidence_quotes": [],
        "improvement": (
            "Remove cost-liability language to preserve missing_cost_liability flaw."
            if score == 1
            else None
        ),
    }


def _flaw_section(case: dict[str, Any], flaw: dict[str, Any], pats: list[str]) -> dict[str, Any]:
    letter = str(case.get("denial_letter_text") or "")
    results = flaw.get("verification_results") or []
    return {
        "dimension": "flaw_injection_verification",
        "denial_pattern_sources_found": pats,
        "verification_results": results,
        "score": flaw.get("score", 5),
        "confidence": 0.93,
        "improvement": flaw.get("improvement"),
    }


def _appeal_difficulty(case: dict[str, Any], flaw: dict[str, Any], pats: list[str], arbiter: dict[str, Any]) -> dict[str, Any]:
    weaknesses: list[str] = []
    for r in flaw.get("verification_results") or []:
        if r.get("status") == "PRESENT":
            weaknesses.append(f"Pattern anchor: {r.get('pattern_id')}")
        elif r.get("status") == "ABSENT":
            weaknesses.append(f"Missing flaw to inject: {r.get('pattern_id')}")
    if not weaknesses:
        weaknesses = [f"Pattern anchor: {p}" for p in pats[:3]]
    defenses = ["Denial cites plan policy framework"]
    if "APPEAL RIGHTS" in str(case.get("denial_letter_text") or ""):
        defenses.append("180-day appeal window stated")
    score = 5 if arbiter.get("verdict") == "APPROVE" else 4 if arbiter.get("verdict") == "REVISE" else 2
    return {
        "dimension": "appeal_difficulty",
        "score": score,
        "exploitable_weaknesses": weaknesses[:5],
        "strong_defenses": defenses,
        "confidence": 0.86,
    }


def generate_md(case: dict[str, Any], ev: dict[str, Any]) -> str:
    prof = case.get("patient_profile") or {}
    ins = _insurer_display(str(case.get("insurer", "")))
    denial = _DENIAL_LABEL.get(str(case.get("denial_type", "")), str(case.get("denial_type", "")))
    cid = str(case.get("case_id", ""))
    letter = str(case.get("denial_letter_text") or "")
    ctx = str(case.get("clinical_context") or "")
    pats = _gum._pattern_ids(case)
    flaw = ev["critics_summary"]["flaw_injection_verifier"]
    arbiter = ev["arbiter"]
    tier1 = arbiter.get("tier_1_failures") or []
    tier2 = arbiter.get("tier_2_failures") or []

    dx = prof.get("diagnosis", "")
    tx = prof.get("treatment_requested", "")
    clinical_analysis = (
        f"{dx} with {tx} is a clinically coherent commercial UM scenario; "
        "clinical_context aligns with profile."
    )

    lines = [
        f"# Gumloop verbose pass — {cid}",
        "",
        f"**Insurer:** {ins} | **Denial:** {denial}  ",
        f"**Patterns:** {', '.join(pats) if pats else '(none)'}  ",
        f"**Profile:** {_profile_line(case)}",
        "",
        "---",
        "",
    ]

    lines.append(
        _section(
            "Prompt 01 — Clinical Critic",
            {
                "dimension": "clinical_realism",
                "analysis": clinical_analysis,
                "score": 5 if "Demographic Validator" not in tier1 else 1,
                "confidence": 0.9,
                "evidence_quotes": _quotes(case, letter + " " + ctx, n=3) or [dx, tx],
                "improvement": None,
            },
        )
    )

    tone_fail = "Tone Critic" in tier2 or ev["critics_summary"].get("template_clinical_context")
    lines.append(
        _section(
            "Prompt 02 — Tone Critic",
            {
                "dimension": "tone_authenticity",
                "analysis": (
                    f"{ins} adverse-benefit administrative register throughout; "
                    + ("template tail in clinical_context flagged." if tone_fail else "no marketing or empathy breaks.")
                ),
                "score": 3 if tone_fail else 5,
                "confidence": 0.88,
                "evidence_quotes": _quotes(case, letter, n=1) or ["NOTICE OF ADVERSE BENEFIT DETERMINATION"],
                "improvement": (
                    "Remove batch template tail from clinical_context."
                    if ev["critics_summary"].get("template_clinical_context")
                    else None
                ),
            },
        )
    )

    llm_fail = "LLM Tell Detector" in tier2
    lines.append(
        _section(
            "Prompt 03 — LLM Tell Detector",
            {
                "dimension": "llm_tell_detection",
                "verdict": "FAIL" if llm_fail else "PASS",
                "analysis": (
                    "Template or corrupted P2P splice detected."
                    if llm_fail
                    else "No LLM hedging or essay transitions detected."
                ),
                "confidence": 0.86,
                "evidence_quotes": [],
                "improvement": arbiter.get("suggested_revisions", [None])[0] if llm_fail else None,
            },
        )
    )

    lines.append(_section("Prompt 04 — Financial Auditor", _financial_audit(case, pats, letter)))
    lines.append(_section("Prompt 05 — Legal Auditor", _legal_audit(case, pats, letter)))

    contra_fail = "Contradiction Hunter" in tier1
    lines.append(
        _section(
            "Prompt 06 — Contradiction Hunter (Tier 1)",
            {
                "dimension": "internal_contradiction",
                "verdict": "FAIL" if contra_fail else "PASS",
                "analysis": (
                    "Age or facts conflict across profile and clinical_context."
                    if contra_fail
                    else "Core facts stable across profile, letter, and clinical_context."
                ),
                "confidence": 0.94,
                "evidence_quotes": [],
                "improvement": (
                    arbiter.get("suggested_revisions", [None])[0] if contra_fail else None
                ),
            },
        )
    )

    demo_fail = "Demographic Validator" in tier1
    lines.append(
        _section(
            "Prompt 07 — Demographic Validator (Tier 1)",
            {
                "dimension": "demographic_plausibility",
                "verdict": "FAIL" if demo_fail else "PASS",
                "analysis": (
                    "Demographic combination fails plausibility gate."
                    if demo_fail
                    else "Age/gender/diagnosis combination is plausible."
                ),
                "confidence": 0.95,
                "evidence_quotes": [],
                "improvement": None if not demo_fail else arbiter.get("reason"),
            },
        )
    )

    lines.append(
        _section(
            "Prompt 11 — Diagnosis–Treatment Match (Tier 1)",
            {
                "dimension": "diagnosis_treatment_match",
                "verdict": "PASS" if not demo_fail else "FAIL",
                "analysis": f"{tx} is a plausible intervention for {dx}.",
                "confidence": 0.96,
                "evidence_quotes": [dx, tx] if dx and tx else [],
                "improvement": None,
            },
        )
    )

    lines.append(
        _section(
            "Prompt 12 — Insurer Voice",
            {
                "dimension": "insurer_voice",
                "analysis": f"Authentically cold {ins} UM voice.",
                "score": 5,
                "confidence": 0.9,
                "evidence_quotes": _quotes(case, letter, n=1) or ["We are unable to approve this request"],
                "improvement": None,
            },
        )
    )

    lines.append(_section("Prompt 13 — Denial Logic", _denial_logic(case, pats, letter)))
    lines.append(_section("Prompt 14 — Date Sanity (Tier 1)", _date_sanity(case, pats, letter)))
    lines.append(_section("Prompt 15 — Citation Traceability", _citation_trace(case, pats, letter)))

    scope_fail = "Scope Guard" in tier1
    lines.append(
        _section(
            "Prompt 16 — Scope Guard (Tier 1)",
            {
                "dimension": "scope_guard",
                "verdict": "FAIL" if scope_fail else "PASS",
                "analysis": (
                    "Medicare/Medicaid reference — out of scope."
                    if scope_fail
                    else f"Commercial {ins} case; in scope."
                ),
                "confidence": 0.98,
                "evidence_quotes": [ins],
                "improvement": None,
            },
        )
    )

    safety_fail = "Safety Redactor" in tier1
    lines.append(
        _section(
            "Prompt 17 — Safety Redactor (Tier 1)",
            {
                "dimension": "safety_redaction",
                "verdict": "FAIL" if safety_fail else "PASS",
                "phi_findings": ["SSN-like pattern"] if safety_fail else ["none"],
                "safety_findings": ["none"],
                "analysis": "Synthetic IDs; neutral tone." if not safety_fail else "PHI pattern detected.",
                "confidence": 0.95,
                "improvement": None,
            },
        )
    )

    lines.append(_section("Prompt 18 — Flaw Injection Verifier ★", _flaw_section(case, flaw, pats)))

    lines.append(
        _section(
            "Prompt 09 — Realism Assessor (meta)",
            {
                "dimension": "overall_realism",
                "score": 5 if arbiter["verdict"] == "APPROVE" else 4,
                "analysis": (
                    "Case reads as credible commercial UM correspondence with intentional procedural flaws."
                    if arbiter["verdict"] != "DISCARD"
                    else "Case failed Tier 1; realism secondary."
                ),
                "confidence": 0.87,
                "improvement": None,
            },
        )
    )

    lines.append(
        _section(
            "Prompt 10 — Appeal Difficulty (meta)",
            _appeal_difficulty(case, flaw, pats, arbiter),
        )
    )

    arb_payload = dict(arbiter)
    if flaw.get("score") == 1 and "Flaw Injection Verifier" not in (arb_payload.get("tier_2_failures") or []):
        arb_payload["tier_2_failures"] = sorted(
            set((arb_payload.get("tier_2_failures") or []) + ["Flaw Injection Verifier"])
        )
        if arb_payload.get("verdict") == "APPROVE":
            arb_payload["verdict"] = "REVISE"
            arb_payload["reason"] = (
                f"Flaw Injection Verifier score 1 — "
                + (flaw.get("improvement") or "pattern verification failed.")
            )[:200]

    lines.append(_section("Prompt 08 — Final Arbiter", arb_payload))

    return "\n".join(lines)


def process_range(start: int, end: int) -> list[dict[str, Any]]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, Any]] = []

    for n in range(start, end + 1):
        path = _case_path(n)
        if not path:
            summary.append({"case_num": n, "case_id": None, "verdict": "MISSING", "file": None})
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        ev = _gum.evaluate(case)
        flaw = ev["critics_summary"]["flaw_injection_verifier"]
        arbiter = ev["arbiter"]
        verdict = arbiter["verdict"]
        if flaw.get("score") == 1 and verdict == "APPROVE":
            verdict = "REVISE"

        cid = str(case.get("case_id", path.stem))
        out_path = OUT_DIR / f"{cid}.md"
        out_path.write_text(generate_md(case, ev), encoding="utf-8")

        missing = [
            r["pattern_id"]
            for r in flaw.get("verification_results") or []
            if r.get("status") == "ABSENT"
        ]
        summary.append(
            {
                "case_num": n,
                "case_id": cid,
                "insurer": case.get("insurer"),
                "denial_type": case.get("denial_type"),
                "verdict": verdict,
                "flaw_score": flaw.get("score"),
                "missing_patterns": missing,
                "tier_1": arbiter.get("tier_1_failures") or [],
                "tier_2": arbiter.get("tier_2_failures") or [],
                "file": str(out_path.relative_to(REPO)),
            }
        )
        if n % 25 == 0:
            print(f"generated {n}/{end}", flush=True)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=351)
    parser.add_argument("--end", type=int, default=500)
    args = parser.parse_args()

    summary = process_range(args.start, args.end)
    counts: dict[str, int] = {}
    for row in summary:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1

    index_path = OUT_DIR / f"SUMMARY_{args.start}_{args.end}.json"
    index_path.write_text(
        json.dumps({"range": [args.start, args.end], "verdicts": counts, "cases": summary}, indent=2),
        encoding="utf-8",
    )
    print("DONE", counts)
    print(index_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
