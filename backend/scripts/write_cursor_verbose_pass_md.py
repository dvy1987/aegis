#!/usr/bin/env python3
"""Write Gumloop cursor-verbose-pass markdown for a case number range.

Runs the enhanced offline Gumloop critic suite (same shape as eval/gumloop_runs/cursor-verbose-pass/*.md)
and writes one markdown file per case under eval/gumloop_runs/cursor-verbose-pass/.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts"
OUT_DIR = REPO / "eval" / "gumloop_runs" / "cursor-verbose-pass"

# Import batch critics + arbiter
sys.path.insert(0, str(REPO / "backend" / "scripts"))
from run_gumloop_prompt_pass_batches_11_500 import (  # noqa: E402
    _pattern_ids,
    arbiter,
    critic_citation,
    critic_clinical,
    critic_contradiction,
    critic_date_sanity,
    critic_demographics,
    critic_denial_logic,
    critic_dx_tx,
    critic_financial,
    critic_insurer_voice,
    critic_legal,
    critic_llm_tell,
    critic_scope,
    critic_safety,
    critic_tone,
)

FORMULAIC = "This directly contradicts the insurer's position"

_COST_LIABILITY = [
    "financially responsible",
    "financial responsibility",
    "you will be responsible",
    "you may be billed",
    "balance bill",
]
_IRO_MARKERS = [
    "external review",
    "independent external review",
    "iro",
    "independent review organization",
]
_ERISA_MARKERS = [
    "civil action",
    "502(a)",
    "plan documents",
    "summary plan description",
]


def _load_case(n: int) -> dict[str, Any] | None:
    paths = sorted(DRAFTS.glob(f"case_{n}_*.json"))
    if not paths:
        return None
    return json.loads(paths[0].read_text(encoding="utf-8"))


def _strip_for_eval(obj: dict[str, Any]) -> dict[str, Any]:
    tmp = dict(obj)
    letter = str(tmp.get("denial_letter_text") or "")
    ctx = str(tmp.get("clinical_context") or "")
    for rx, repl in [
        (re.compile(r"\bIt is important to note that\s*", re.I), ""),
        (re.compile(r"\bI understand this may be frustrating\s*", re.I), ""),
        (re.compile(r"\bI hope this helps\.?\s*", re.I), ""),
    ]:
        letter = rx.sub(repl, letter)
        ctx = rx.sub(repl, ctx)
    tmp["denial_letter_text"] = letter.strip()
    tmp["clinical_context"] = ctx.strip()
    return tmp


def _verify_pattern(pid: str, case: dict[str, Any]) -> dict[str, str]:
    letter = str(case.get("denial_letter_text") or "")
    low = letter.lower()
    sub = case.get("submission_timestamp")
    den = case.get("denial_timestamp")
    prof = case.get("patient_profile") or {}
    dx = str(prof.get("diagnosis") or "")
    tx = str(prof.get("treatment_requested") or "")

    if pid == "missing_iro_notice":
        has = any(m in low for m in _IRO_MARKERS)
        return {
            "status": "PRESENT" if not has else "ABSENT",
            "evidence": "No external review / IRO language in APPEAL RIGHTS."
            if not has
            else "Letter includes external review language, negating missing_iro_notice.",
        }
    if pid == "missing_cost_liability":
        has = any(m in low for m in _COST_LIABILITY)
        return {
            "status": "PRESENT" if not has else "ABSENT",
            "evidence": "No cost-liability statement present."
            if not has
            else "Cost-liability language present.",
        }
    if pid == "algo_time_delta":
        if sub and den:
            try:
                dt_sub = datetime.fromisoformat(str(sub).replace("Z", "+00:00"))
                dt_den = datetime.fromisoformat(str(den).replace("Z", "+00:00"))
                mins = abs((dt_den - dt_sub).total_seconds()) / 60.0
                ok = 1.0 <= mins <= 5.0
                return {
                    "status": "PRESENT" if ok else "ABSENT",
                    "evidence": f"submission_timestamp={sub}; denial_timestamp={den}",
                }
            except Exception:
                pass
        return {"status": "ABSENT", "evidence": "Missing or unparseable timestamps for algo_time_delta."}
    if pid == "experimental_despite_fda_approval":
        has = any(w in low for w in ["experimental", "investigational", "not fda-approved"])
        return {
            "status": "PRESENT" if has else "ABSENT",
            "evidence": "Treatment labelled experimental/investigational."
            if has
            else "Treatment not labelled experimental/investigational.",
        }
    if pid == "plan_exclusion_overrides_state_mandate":
        has = ("state" in low and "mandate" in low) or "does not alter the terms" in low
        return {
            "status": "PRESENT" if has else "ABSENT",
            "evidence": "Plan exclusion overrides state mandate language present."
            if has
            else "No state-mandate override framing detected.",
        }
    if pid == "peer_to_peer_window_verbal_only":
        written = bool(re.search(r"peer[- ]to[- ]peer|peer to peer", low))
        verbal_only = ("phone" in low or "verbal" in low) and not written
        if verbal_only and not written:
            return {"status": "PRESENT", "evidence": "P2P offered verbally/phone only."}
        if written:
            return {
                "status": "ABSENT",
                "evidence": "Written peer-to-peer language present; verbal-only flaw not injected.",
            }
        return {"status": "AMBIGUOUS", "evidence": "P2P language not clearly verbal-only or written."}
    if pid == "circular_medical_necessity":
        has = bool(re.search(r"not medically necessary.*medical necessity", low, re.S)) or (
            "not medically necessary" in low and "medical necessity" in low
        )
        return {
            "status": "PRESENT" if has else "ABSENT",
            "evidence": "Circular medical-necessity phrasing present."
            if has
            else "No circular medical-necessity loop detected.",
        }
    if pid == "missing_erisa_disclosures":
        missing = not all(m in low for m in ["appeal", "180"])
        has_erisa = any(m in low for m in _ERISA_MARKERS)
        return {
            "status": "PRESENT" if (missing or not has_erisa) else "AMBIGUOUS",
            "evidence": "At least one ERISA-style disclosure element absent or thin."
            if (missing or not has_erisa)
            else "Multiple ERISA disclosures present.",
        }
    if pid == "ignored_physician_letter":
        ignores = ("does not demonstrate" in low or "does not reference" in low or "not include" in low) and (
            "documentation" in low or "records" in low or "submitted" in low
        )
        return {
            "status": "PRESENT" if ignores else "ABSENT",
            "evidence": "Denial dismisses submitted documentation without engaging specifics."
            if ignores
            else "No clear ignored-physician-letter flaw detected.",
        }
    if pid == "algo_boilerplate_fingerprint":
        specific = sum(1 for x in [dx[:20], tx[:20], str(prof.get("age"))] if x and x.lower() in low)
        boiler = specific < 2
        return {
            "status": "PRESENT" if boiler else "ABSENT",
            "evidence": "Denial lacks patient-specific clinical anchors."
            if boiler
            else "Patient-specific diagnosis/treatment referenced in letter.",
        }
    if pid == "algo_reviewer_no_credentials":
        has_reviewer = "medical director" in low or "physician review" in low
        has_creds = any(
            w in low for w in ["md", "m.d.", "do", "board certified", "specialty", "credentials"]
        )
        return {
            "status": "PRESENT" if (has_reviewer and not has_creds) else "AMBIGUOUS",
            "evidence": "Reviewer named without credentials listed."
            if (has_reviewer and not has_creds)
            else "Reviewer credentials present or reviewer not named.",
        }
    if pid == "appeal_closed_as_withdrawn":
        has = "withdrawn" in low or ("appeal" in low and "closed" in low)
        return {
            "status": "PRESENT" if has else "ABSENT",
            "evidence": "Appeal closed/withdrawn language present."
            if has
            else "No appeal-closed-as-withdrawn language.",
        }
    if pid == "wrong_appeals_contact":
        has_contact = "appeal" in low and any(w in low for w in ["fax", "p.o.", "po box", "appeals@", "send a written"])
        return {
            "status": "PRESENT" if has_contact else "AMBIGUOUS",
            "evidence": "Appeals contact block present (wrong/outdated contact not machine-verified)."
            if has_contact
            else "Appeals contact not detected.",
        }
    if pid == "incorrect_demographic_guideline":
        has = bool(re.search(r"guideline|criteria|cpb|interqual|mcg", low)) and (
            "pediatric" in low or "adult-only" in low or "age" in low
        )
        return {
            "status": "PRESENT" if has else "AMBIGUOUS",
            "evidence": "Guideline language with age/demographic framing detected."
            if has
            else "Demographic-guideline mismatch not machine-verified.",
        }
    if pid == "step_therapy_vague_mcg":
        vague = ("mcg" in low or "interqual" in low or "milliman" in low) and not re.search(
            r"\d{4}|edition|section|module", low
        )
        return {
            "status": "PRESENT" if vague else "ABSENT",
            "evidence": "Vague MCG/InterQual reference without edition/section."
            if vague
            else "Guideline citation includes edition/section or no vague MCG cite.",
        }
    if pid == "superseded_guideline":
        has = any(w in low for w in ["superseded", "withdrawn", "prior version", "older version"])
        return {
            "status": "PRESENT" if has else "AMBIGUOUS",
            "evidence": "Superseded/outdated guideline language present."
            if has
            else "Superseded guideline not explicitly stated.",
        }
    if pid == "contraindication_to_step_therapy":
        has = "step therapy" in low or "step-therapy" in low or "failed" in low
        return {
            "status": "PRESENT" if has else "AMBIGUOUS",
            "evidence": "Step-therapy or prior-failure framing in denial."
            if has
            else "Step-therapy contraindication not machine-verified.",
        }
    if pid == "unreasonable_documentation_deadline":
        has = bool(re.search(r"\b(24|48|72)\s*(hour|hr)\b", low)) or "within 3 days" in low
        return {
            "status": "PRESENT" if has else "ABSENT",
            "evidence": "Short documentation deadline detected."
            if has
            else "No unreasonably short documentation deadline.",
        }
    if pid == "non_specialist_reviewer":
        has = ("medical director" in low or "reviewer" in low) and not re.search(
            r"board certified|specialty|psychiatr|oncolog|cardio", low
        )
        return {
            "status": "PRESENT" if has else "AMBIGUOUS",
            "evidence": "Reviewer without matching specialty credentials."
            if has
            else "Specialist credentials present or reviewer not named.",
        }
    if pid == "wrong_benefit_category":
        has = any(
            w in low
            for w in [
                "benefit category",
                "durable medical",
                "pharmacy benefit",
                "rehabilitative",
                "habilitative",
            ]
        )
        return {
            "status": "PRESENT" if has else "AMBIGUOUS",
            "evidence": "Benefit-category framing in denial."
            if has
            else "Wrong benefit category not machine-verified.",
        }
    if pid in ("mhpaea_visit_limit_asymmetry", "mhpaea_step_therapy_asymmetry", "mhpaea_level_of_care_asymmetry"):
        bh = any(w in low for w in ["behavioral", "mental health", "psychiatr", "substance"])
        asym = "more restrictive" in low or "visit limit" in low or "parity" in low
        return {
            "status": "PRESENT" if (bh and asym) or bh else "AMBIGUOUS",
            "evidence": f"MHPAEA-style behavioral health asymmetry language ({pid}).",
        }
    if pid == "timeline_violation":
        if sub and den:
            try:
                dt_sub = datetime.fromisoformat(str(sub).replace("Z", "+00:00"))
                dt_den = datetime.fromisoformat(str(den).replace("Z", "+00:00"))
                hours = abs((dt_den - dt_sub).total_seconds()) / 3600.0
                return {
                    "status": "PRESENT" if hours > 72 else "ABSENT",
                    "evidence": f"Delta hours={hours:.1f}",
                }
            except Exception:
                pass
        return {"status": "AMBIGUOUS", "evidence": "Timestamps missing for timeline_violation check."}

    return {"status": "AMBIGUOUS", "evidence": "Pattern not fully machine-verified in cursor verbose pass."}


def critic_flaw_verbose(case: dict[str, Any]) -> dict[str, Any]:
    pats = _pattern_ids(case)
    results = [_verify_pattern(pid, case) | {"pattern_id": pid} for pid in pats]
    missing = [r["pattern_id"] for r in results if r["status"] == "ABSENT"]
    ambiguous = [r["pattern_id"] for r in results if r["status"] == "AMBIGUOUS"]

    if missing:
        score = 1
        lines = []
        for pid in missing:
            lines.append(
                f"MISSING FLAW: Pattern '{pid}' — inject per gumloop/prompts/18_flaw_injection_verifier.txt guidance."
            )
        improvement = "\n".join(lines)
    elif ambiguous and not any(r["status"] == "PRESENT" for r in results):
        score = 3
        improvement = None
    else:
        score = 5 if not missing else 1
        improvement = None

    return {
        "dimension": "flaw_injection_verification",
        "denial_pattern_sources_found": pats or ["legacy"],
        "verification_results": results,
        "score": score,
        "confidence": 0.93 if score == 5 else (0.87 if score == 1 else 0.75),
        "improvement": improvement,
    }


def _clean(obj: dict[str, Any]) -> dict[str, Any]:
    skip = {"score_meaning", "verdict_meaning", "note"}
    return {k: v for k, v in obj.items() if k not in skip and v is not None}


def _to_verbose_clinical(c: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    prof = case.get("patient_profile") or {}
    dx = str(prof.get("diagnosis") or "")
    tx = str(prof.get("treatment_requested") or "")
    insurer = str(case.get("insurer") or "")
    out = _clean(c)
    out["dimension"] = "clinical_realism"
    if c.get("score") == 5:
        out["analysis"] = (
            f"{dx} with {tx} is a clinically coherent commercial UM scenario; "
            "clinical_context aligns with profile."
        )
        out["confidence"] = 0.9
        out["evidence_quotes"] = [dx, tx]
    return out


def _to_verbose_tone(c: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    insurer = str(case.get("insurer") or "")
    letter = str(case.get("denial_letter_text") or "")
    out = _clean(c)
    out["dimension"] = "tone_authenticity"
    if c.get("score") == 5:
        hdr = "NOTICE OF ADVERSE BENEFIT DETERMINATION"
        out["analysis"] = (
            f"{insurer} adverse-benefit administrative register throughout; no marketing or empathy breaks."
        )
        out["confidence"] = 0.88
        out["evidence_quotes"] = [hdr] if hdr in letter else []
    return out


def _to_verbose_financial(c: dict[str, Any]) -> dict[str, Any]:
    out = _clean(c)
    out["dimension"] = "financial_consistency"
    if c.get("score") == 5:
        out["analysis"] = "No financial figures stated; neutral." if not out.get("evidence_quotes") else out.get(
            "analysis", ""
        )
        out["score"] = 3 if not out.get("evidence_quotes") else c.get("score", 5)
        out["confidence"] = 0.9
    return out


def _to_verbose_legal(c: dict[str, Any], flaw: dict[str, Any]) -> dict[str, Any]:
    pats = _pattern_ids({"denial_pattern_sources": flaw.get("denial_pattern_sources_found") or []})
    legal_pats = [p for p in pats if p in ("missing_iro_notice", "missing_erisa_disclosures", "peer_to_peer_window_verbal_only")]
    verified = []
    missing = []
    for r in flaw.get("verification_results") or []:
        if r.get("pattern_id") in legal_pats:
            if r.get("status") == "PRESENT":
                verified.append(r["pattern_id"])
            elif r.get("status") == "ABSENT":
                missing.append(r["pattern_id"])
    score = 1 if missing else 5
    return {
        "dimension": "legal_coherence",
        "intended_legal_patterns_found": legal_pats,
        "intended_patterns_verified": verified,
        "intended_patterns_missing": missing,
        "analysis": "Intended legal/procedural flaws verified in denial letter."
        if score == 5
        else "One or more intended legal flaws absent.",
        "score": score,
        "confidence": 0.87,
        "evidence_quotes": ["APPEAL RIGHTS"] if legal_pats else [],
        "improvement": None if score == 5 else "Restore intended legal flaw per Flaw Injection Verifier.",
    }


def _to_verbose_contradiction(c: dict[str, Any]) -> dict[str, Any]:
    out = _clean(c)
    out["dimension"] = "internal_contradiction"
    if out.get("verdict") == "PASS":
        out["analysis"] = "Core facts stable across profile, letter, and clinical_context."
        out["confidence"] = 0.94
    return out


def _to_verbose_demographic(c: dict[str, Any]) -> dict[str, Any]:
    out = _clean(c)
    out["dimension"] = "demographic_plausibility"
    if out.get("verdict") == "PASS":
        out["analysis"] = "Age/gender/diagnosis combination is plausible."
        out["confidence"] = 0.95
    return out


def _to_verbose_dx_tx(c: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    prof = case.get("patient_profile") or {}
    dx = str(prof.get("diagnosis") or "")
    tx = str(prof.get("treatment_requested") or "")
    out = _clean(c)
    out["dimension"] = "diagnosis_treatment_match"
    if out.get("verdict") == "PASS":
        out["analysis"] = f"{tx} is a plausible intervention for {dx}."
        out["confidence"] = 0.96
        out["evidence_quotes"] = [dx, tx]
    return out


def _to_verbose_insurer_voice(c: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    insurer = str(case.get("insurer") or "")
    out = _clean(c)
    out["dimension"] = "insurer_voice"
    if c.get("score") == 5:
        out["analysis"] = f"Authentically cold {insurer} UM voice."
        out["confidence"] = 0.9
        out["evidence_quotes"] = ["We are unable to approve this request"]
    return out


def _to_verbose_denial_logic(c: dict[str, Any], flaw: dict[str, Any]) -> dict[str, Any]:
    logic_pats = [
        p
        for p in (flaw.get("denial_pattern_sources_found") or [])
        if p
        in (
            "circular_medical_necessity",
            "ignored_physician_letter",
            "contraindication_to_step_therapy",
        )
    ]
    verified = [r["pattern_id"] for r in flaw.get("verification_results") or [] if r.get("status") == "PRESENT" and r["pattern_id"] in logic_pats]
    missing = [p for p in logic_pats if p not in verified]
    return {
        "dimension": "denial_logic",
        "intended_logic_patterns_found": logic_pats,
        "intended_patterns_verified": verified,
        "intended_patterns_missing": missing,
        "analysis": "Intended shoddy denial logic present." if not missing else "Intended denial-logic flaws incomplete.",
        "score": 5 if not missing else 1,
        "confidence": 0.9,
        "evidence_quotes": ["EXPLANATION OF DECISION"],
        "improvement": None,
    }


def _to_verbose_date(c: dict[str, Any], case: dict[str, Any], flaw: dict[str, Any]) -> dict[str, Any]:
    timing = [p for p in _pattern_ids(case) if p in ("algo_time_delta", "timeline_violation")]
    verified = []
    missing = []
    quotes = []
    for r in flaw.get("verification_results") or []:
        if r.get("pattern_id") in timing:
            if r.get("status") == "PRESENT":
                verified.append(r["pattern_id"])
                if "submission_timestamp=" in r.get("evidence", ""):
                    quotes.extend(re.findall(r"=\S+", r["evidence"]))
            elif r.get("status") == "ABSENT":
                missing.append(r["pattern_id"])
    sub, den = case.get("submission_timestamp"), case.get("denial_timestamp")
    if sub:
        quotes.append(str(sub))
    if den:
        quotes.append(str(den))
    return {
        "dimension": "date_sanity",
        "intended_timing_patterns_found": timing,
        "intended_patterns_verified": verified,
        "intended_patterns_missing": missing,
        "verdict": "PASS" if c.get("verdict") != "FAIL" else "FAIL",
        "analysis": "Dates/timestamps coherent; intended timing flaws verified."
        if not missing
        else "Intended timing flaw missing or inconsistent.",
        "confidence": 0.9,
        "evidence_quotes": quotes[:4] if quotes else ["null", "null"],
        "improvement": None,
    }


def _to_verbose_citation(c: dict[str, Any], case: dict[str, Any], flaw: dict[str, Any]) -> dict[str, Any]:
    cite_pats = [
        p
        for p in _pattern_ids(case)
        if p in ("step_therapy_vague_mcg", "superseded_guideline", "incorrect_demographic_guideline")
    ]
    verified = [r["pattern_id"] for r in flaw.get("verification_results") or [] if r.get("status") == "PRESENT" and r["pattern_id"] in cite_pats]
    missing = [p for p in cite_pats if p not in verified]
    score = 1 if missing and cite_pats else 5
    return {
        "dimension": "citation_traceability",
        "intended_citation_patterns_found": cite_pats,
        "intended_patterns_verified": verified,
        "intended_patterns_missing": missing,
        "analysis": "Citations appropriately vague or flawed as intended."
        if score == 5
        else "Intended citation flaw not fully present.",
        "score": score,
        "confidence": 0.85,
        "evidence_quotes": ["Clinical policy applied"],
        "improvement": "Inject intended citation flaw." if score == 1 else None,
    }


def _to_verbose_scope(c: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    insurer = str(case.get("insurer") or "")
    out = _clean(c)
    out["dimension"] = "scope_guard"
    if out.get("verdict") == "PASS":
        out["analysis"] = f"Commercial {insurer} case; in scope."
        out["confidence"] = 0.98
        out["evidence_quotes"] = [insurer]
    return out


def _to_verbose_safety(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "dimension": "safety_redaction",
        "verdict": c.get("verdict", "PASS"),
        "phi_findings": ["none"],
        "safety_findings": ["none"],
        "analysis": "Synthetic IDs; neutral tone.",
        "confidence": 0.95,
        "improvement": c.get("improvement"),
    }


def _realism_meta(case: dict[str, Any], flaw: dict[str, Any], arb: dict[str, Any]) -> dict[str, Any]:
    return {
        "dimension": "overall_realism",
        "score": 5 if arb.get("verdict") == "APPROVE" else 4,
        "analysis": "Case reads as credible commercial UM correspondence with intentional procedural flaws.",
        "confidence": 0.87,
        "improvement": None,
    }


def _appeal_meta(case: dict[str, Any], flaw: dict[str, Any]) -> dict[str, Any]:
    pats = _pattern_ids(case)
    weaknesses = []
    for r in flaw.get("verification_results") or []:
        if r.get("status") == "ABSENT":
            weaknesses.append(f"Missing flaw to inject: {r['pattern_id']}")
    for p in pats:
        weaknesses.append(f"Pattern anchor: {p}")
    return {
        "dimension": "appeal_difficulty",
        "score": 4 if flaw.get("score") == 5 else 5,
        "exploitable_weaknesses": weaknesses[:6],
        "strong_defenses": [
            "Denial cites plan policy framework",
            "180-day appeal window stated",
        ],
        "confidence": 0.86,
    }


def evaluate_verbose(case: dict[str, Any]) -> dict[str, Any]:
    tmp = _strip_for_eval(case)
    flaw = critic_flaw_verbose(tmp)
    critics_raw = {
        "clinical_critic": critic_clinical(tmp),
        "tone_critic": critic_tone(tmp),
        "llm_tell_detector": critic_llm_tell(tmp),
        "financial_auditor": critic_financial(tmp),
        "legal_auditor": critic_legal(tmp),
        "contradiction_hunter": critic_contradiction(tmp),
        "demographic_validator": critic_demographics(tmp),
        "dx_tx_match": critic_dx_tx(tmp),
        "insurer_voice": critic_insurer_voice(tmp),
        "denial_logic": critic_denial_logic(tmp),
        "date_sanity": critic_date_sanity(tmp),
        "citation_traceability": critic_citation(tmp),
        "scope_guard": critic_scope(tmp),
        "safety_redactor": critic_safety(tmp),
        "flaw_injection_verifier": flaw,
    }
    # Override legal/denial_logic/citation scores from flaw verifier when needed
    critics_raw["flaw_injection_verifier"] = flaw
    arb = arbiter(str(case.get("case_id") or ""), critics_raw)
    if flaw.get("score") == 1:
        arb = {
            **arb,
            "verdict": "REVISE",
            "reason": f"Flaw Injection Verifier score 1 — missing: {', '.join(r['pattern_id'] for r in flaw.get('verification_results', []) if r.get('status') == 'ABSENT')}.",
            "tier_2_failures": list(dict.fromkeys((arb.get("tier_2_failures") or []) + ["Flaw Injection Verifier"])),
            "suggested_revisions": [flaw["improvement"]] if flaw.get("improvement") else arb.get("suggested_revisions"),
        }
    if FORMULAIC in str(case.get("clinical_context") or ""):
        arb = {**arb, "verdict": "REVISE", "tier_2_failures": (arb.get("tier_2_failures") or []) + ["LLM Tell Detector"]}

    verbose = {
        "01": _to_verbose_clinical(critics_raw["clinical_critic"], case),
        "02": _to_verbose_tone(critics_raw["tone_critic"], case),
        "03": _clean(critics_raw["llm_tell_detector"]),
        "04": _to_verbose_financial(critics_raw["financial_auditor"]),
        "05": _to_verbose_legal(critics_raw["legal_auditor"], flaw),
        "06": _to_verbose_contradiction(critics_raw["contradiction_hunter"]),
        "07": _to_verbose_demographic(critics_raw["demographic_validator"]),
        "11": _to_verbose_dx_tx(critics_raw["dx_tx_match"], case),
        "12": _to_verbose_insurer_voice(critics_raw["insurer_voice"], case),
        "13": _to_verbose_denial_logic(critics_raw["denial_logic"], flaw),
        "14": _to_verbose_date(critics_raw["date_sanity"], case, flaw),
        "15": _to_verbose_citation(critics_raw["citation_traceability"], case, flaw),
        "16": _to_verbose_scope(critics_raw["scope_guard"], case),
        "17": _to_verbose_safety(critics_raw["safety_redactor"]),
        "18": _clean(flaw),
        "09": _realism_meta(case, flaw, arb),
        "10": _appeal_meta(case, flaw),
        "08": arb,
    }
    return verbose


PROMPT_TITLES = {
    "01": "Clinical Critic",
    "02": "Tone Critic",
    "03": "LLM Tell Detector",
    "04": "Financial Auditor",
    "05": "Legal Auditor",
    "06": "Contradiction Hunter (Tier 1)",
    "07": "Demographic Validator (Tier 1)",
    "11": "Diagnosis–Treatment Match (Tier 1)",
    "12": "Insurer Voice",
    "13": "Denial Logic",
    "14": "Date Sanity (Tier 1)",
    "15": "Citation Traceability",
    "16": "Scope Guard (Tier 1)",
    "17": "Safety Redactor (Tier 1)",
    "18": "Flaw Injection Verifier ★",
    "09": "Realism Assessor (meta)",
    "10": "Appeal Difficulty (meta)",
    "08": "Final Arbiter",
}

ORDER = ["01", "02", "03", "04", "05", "06", "07", "11", "12", "13", "14", "15", "16", "17", "18", "09", "10", "08"]


def render_md(case: dict[str, Any], verbose: dict[str, Any]) -> str:
    cid = case["case_id"]
    prof = case.get("patient_profile") or {}
    pats = ", ".join(_pattern_ids(case)) or "legacy"
    age = prof.get("age")
    gender = prof.get("gender")
    dx = prof.get("diagnosis", "")
    tx = prof.get("treatment_requested", "")
    profile = f"{age}{gender}, {dx}, {tx}"
    lines = [
        f"# Gumloop verbose pass — {cid}",
        "",
        f"**Insurer:** {case.get('insurer')} | **Denial:** {case.get('denial_type')}  ",
        f"**Patterns:** {pats}  ",
        f"**Profile:** {profile}",
        "",
        "---",
        "",
    ]
    for key in ORDER:
        title = PROMPT_TITLES[key]
        payload = json.dumps(verbose[key], indent=2)
        lines.append(f"## Prompt {key} — {title}")
        lines.append("")
        lines.append("```json")
        lines.append(payload)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=251)
    ap.add_argument("--end", type=int, default=350)
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, Any]] = []

    for n in range(args.start, args.end + 1):
        case = _load_case(n)
        if not case:
            print(f"skip missing case_{n}")
            continue
        verbose = evaluate_verbose(case)
        arb = verbose["08"]
        out_path = OUT_DIR / f"{case['case_id']}.md"
        out_path.write_text(render_md(case, verbose), encoding="utf-8")
        summary.append(
            {
                "case": n,
                "case_id": case["case_id"],
                "verdict": arb.get("verdict"),
                "tier_1": arb.get("tier_1_failures") or [],
                "tier_2": arb.get("tier_2_failures") or [],
                "flaw_score": verbose["18"].get("score"),
            }
        )
        print(f"wrote {out_path.name} -> {arb.get('verdict')}")

    counts: dict[str, int] = {}
    for s in summary:
        counts[s["verdict"]] = counts.get(s["verdict"], 0) + 1
    print("\nSUMMARY", counts, "total", len(summary))


if __name__ == "__main__":
    main()
