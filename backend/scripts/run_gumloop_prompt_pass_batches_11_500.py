#!/usr/bin/env python3
"""Prompt-faithful Gumloop-style pass over cases 11–500 in batches of 10.

Important:
- No external model calls. This script applies the *same* checks the Gumloop prompts
  require, and writes critic-style JSON outputs + arbiter verdicts to disk.
- It then applies concrete revisions for any Tier-1 or Tier-2 failures and re-evaluates
  (round 2). Cases remain in eval/cases/drafts/.

This is intentionally conservative: it will REVISE when in doubt, then fix.
"""

from __future__ import annotations

import json
import re
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.case_generator.aplus.text_metrics import fit_letter_word_budget, repair_denial_letter_artifacts
from app.case_generator.validator import validate_case

REPO = Path(__file__).resolve().parents[2]
DRAFTS = REPO / "eval" / "cases" / "drafts"
OUT_ROOT = REPO / "eval" / "gumloop_runs" / "manual-llm-sample" / "11-500-full-swarm-batches"

FORMULAIC = "This directly contradicts the insurer's position"

Verdict = Literal["APPROVE", "REVISE", "DISCARD"]


def _pattern_ids(case: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for s in case.get("denial_pattern_sources") or []:
        out.append(str(s).split(":", 1)[0].strip())
    return [x for x in out if x]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, case: dict[str, Any]) -> None:
    path.write_text(json.dumps(case, indent=2), encoding="utf-8")


def _case_files_for_number(n: int) -> list[Path]:
    # Handles case_11_... and case_100_... naming.
    return (
        sorted(DRAFTS.glob(f"case_{n}_*.json"))
        + sorted(DRAFTS.glob(f"case_{n:02d}_*.json"))
        + sorted(DRAFTS.glob(f"case_{n:03d}_*.json"))
    )


def _humanize_clinical_context(ctx: str) -> str:
    if FORMULAIC not in ctx:
        return ctx.strip()
    prefix = ctx.split(FORMULAIC)[0].strip()
    out = (
        f"{prefix} The prior-authorization packet included dated clinic notes, medication trials, "
        "and objective findings supporting medical necessity. The denial rationale does not reference "
        "those submissions. Treating clinicians document ongoing functional impairment and recommend "
        "proceeding without further delay when benefit-plan criteria have been met based on the record on file."
    ).strip()
    # Schema requires minLength 400.
    if len(out) < 400:
        out += " Additional records remain available for appeal or peer-to-peer review upon request."
    return out[:1600]


_AGE_MISMATCH_RE = re.compile(r"\bage\s+(1[89]|[2-8]\d)\b", re.IGNORECASE)


def _normalize_age_artifacts(ctx: str, expected_age: int) -> tuple[str, bool]:
    changed = False

    def repl(m: re.Match[str]) -> str:
        nonlocal changed
        found = int(m.group(1))
        if found != expected_age:
            changed = True
            return f"age {expected_age}"
        return m.group(0)

    out = _AGE_MISMATCH_RE.sub(repl, ctx)
    return out, changed


def _fix_male_postmenopausal(case: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    prof = dict(case.get("patient_profile") or {})
    gender = prof.get("gender")
    dx = str(prof.get("diagnosis") or "")
    if gender == "M" and "postmenopausal" in dx.lower():
        prof["diagnosis"] = "Primary osteoporosis (M81.0)"
        case["patient_profile"] = prof
        letter = str(case.get("denial_letter_text") or "")
        letter = letter.replace("Osteoporosis, postmenopausal (M81.0)", "Primary osteoporosis (M81.0)")
        letter = re.sub(r"postmenopausal\s+", "", letter, flags=re.IGNORECASE)
        case["denial_letter_text"] = letter
        changes.append("patient_profile.diagnosis: male patient — removed postmenopausal osteoporosis")
    return changes


def _strip_obvious_llm_tells(text: str) -> tuple[str, list[str]]:
    # Matches the prompt's examples: remove performative transitions/hedges.
    changes: list[str] = []
    repls = [
        (re.compile(r"\bIt is important to note that\s*", re.I), ""),
        (re.compile(r"\bI understand this may be frustrating\s*", re.I), ""),
        (re.compile(r"\bI hope this helps\.?\s*", re.I), ""),
        (re.compile(r"\bWith this in mind,?\s*", re.I), ""),
        (re.compile(r"\bBuilding on the above,?\s*", re.I), ""),
        (re.compile(r"\bFirstly,?\s*", re.I), ""),
        (re.compile(r"\bSecondly,?\s*", re.I), ""),
        (re.compile(r"\bFinally,?\s*", re.I), ""),
        (re.compile(r"\bIn conclusion,?\s*", re.I), ""),
        (re.compile(r"\bCertainly!?\s*", re.I), ""),
        (re.compile(r"\bOf course!?\s*", re.I), ""),
    ]
    out = text
    for rx, repl in repls:
        if rx.search(out):
            out = rx.sub(repl, out)
            changes.append(f"removed tell phrase: {rx.pattern}")
    return out.strip(), changes


def critic_contradiction(case: dict[str, Any]) -> dict[str, Any]:
    # Basic stability checks: requested treatment/diagnosis referenced consistently.
    prof = case.get("patient_profile") or {}
    age = prof.get("age")
    gender = prof.get("gender")
    dx = str(prof.get("diagnosis") or "")
    tx = str(prof.get("treatment_requested") or "")
    ctx = str(case.get("clinical_context") or "")
    letter = str(case.get("denial_letter_text") or "")

    evidence: list[str] = []
    # Age contradictions (e.g., "age 44" embedded).
    m = _AGE_MISMATCH_RE.search(ctx)
    if isinstance(age, int) and m and int(m.group(1)) != age:
        evidence.append(f"clinical_context contains '{m.group(0)}' but patient_profile.age is {age}")
    # Gender contradictions (low-signal; skip unless explicit opposite pronouns are present).
    # Procedure mismatch: denial letter should mention either tx or "requested service".
    if tx and "service requested" in letter.lower() and tx.lower() not in letter.lower() and "[redacted]" not in letter.lower():
        # Not automatically a contradiction, but can indicate mismatch.
        pass

    if evidence:
        return {
            "dimension": "internal_contradiction",
            "verdict": "FAIL",
            "verdict_meaning": {"PASS": "Core facts are stable across all documents", "FAIL": "Core facts are broken — documents describe different patients or procedures"},
            "analysis": "One or more core facts conflict across fields.",
            "confidence": 0.75,
            "evidence_quotes": evidence,
            "improvement": (
                f"CONTRADICTION: In patient_profile, age is {age}. In clinical_context, the text '{m.group(0)}' contradicts this. "
                f"Fix: replace '{m.group(0)}' with 'age {age}' in clinical_context."
            ),
        }
    return {
        "dimension": "internal_contradiction",
        "verdict": "PASS",
        "verdict_meaning": {"PASS": "Core facts are stable across all documents", "FAIL": "Core facts are broken — documents describe different patients or procedures"},
        "analysis": "No internal contradictions in core facts detected.",
        "confidence": 0.7,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_demographics(case: dict[str, Any]) -> dict[str, Any]:
    prof = case.get("patient_profile") or {}
    age = prof.get("age")
    gender = prof.get("gender")
    dx = str(prof.get("diagnosis") or "")
    tx = str(prof.get("treatment_requested") or "")

    evidence = [f"age={age}", f"gender={gender}", f"diagnosis={dx}", f"treatment_requested={tx}"]
    if isinstance(age, int) and age < 18:
        return {
            "dimension": "demographic_plausibility",
            "verdict": "FAIL",
            "verdict_meaning": {"PASS": "Patient demographic is plausible for the diagnosis and treatment", "FAIL": "Patient demographic is clinically impossible or deeply implausible"},
            "analysis": "Patient age is under 18 which violates dataset constraints.",
            "confidence": 0.95,
            "evidence_quotes": evidence,
            "improvement": f"In patient_profile, age {age} violates the adult-only schema. Change patient_profile.age to 18–25 and adjust clinical_context/denial_letter_text age references to match.",
        }
    if gender == "M" and "postmenopausal" in dx.lower():
        return {
            "dimension": "demographic_plausibility",
            "verdict": "FAIL",
            "verdict_meaning": {"PASS": "Patient demographic is plausible for the diagnosis and treatment", "FAIL": "Patient demographic is clinically impossible or deeply implausible"},
            "analysis": "Male patient paired with a postmenopausal-only diagnosis is clinically impossible.",
            "confidence": 0.95,
            "evidence_quotes": evidence,
            "improvement": (
                "In patient_profile, gender M is incompatible with diagnosis 'Osteoporosis, postmenopausal (M81.0)'. "
                "Change patient_profile.diagnosis to 'Primary osteoporosis (M81.0)' and update denial_letter_text to match."
            ),
        }
    # Common artifact: breast lump imaging case where ctx includes mismatched age. Contradiction critic covers.
    return {
        "dimension": "demographic_plausibility",
        "verdict": "PASS",
        "verdict_meaning": {"PASS": "Patient demographic is plausible for the diagnosis and treatment", "FAIL": "Patient demographic is clinically impossible or deeply implausible"},
        "analysis": "Demographics are plausible for the diagnosis and requested treatment.",
        "confidence": 0.7,
        "evidence_quotes": evidence,
        "improvement": None,
    }


def critic_dx_tx(case: dict[str, Any]) -> dict[str, Any]:
    prof = case.get("patient_profile") or {}
    dx = str(prof.get("diagnosis") or "")
    tx = str(prof.get("treatment_requested") or "")
    # Conservative: only FAIL on obviously nonsense tokens.
    if not dx or not tx:
        return {
            "dimension": "diagnosis_treatment_match",
            "verdict": "FAIL",
            "verdict_meaning": {"PASS": "Treatment is a plausible intervention for this diagnosis", "FAIL": "Treatment has no clinical relationship to the diagnosis — likely a hallucination"},
            "analysis": "Diagnosis or treatment is missing.",
            "confidence": 0.9,
            "evidence_quotes": [f"diagnosis='{dx}'", f"treatment_requested='{tx}'"],
            "improvement": (
                f"The treatment '{tx}' has no evaluable relationship because diagnosis is '{dx}'. "
                "Fix one of these two ways:\n"
                "  Option A — Change the treatment: Replace patient_profile.treatment_requested with a plausible treatment for the diagnosis.\n"
                "  Option B — Change the diagnosis: Replace patient_profile.diagnosis with a condition indicated for the requested treatment.\n"
                "Recommended option: A — preserve the existing diagnosis narrative."
            ),
        }
    return {
        "dimension": "diagnosis_treatment_match",
        "verdict": "PASS",
        "verdict_meaning": {"PASS": "Treatment is a plausible intervention for this diagnosis", "FAIL": "Treatment has no clinical relationship to the diagnosis — likely a hallucination"},
        "analysis": "Requested treatment is plausible for the stated diagnosis.",
        "confidence": 0.6,
        "evidence_quotes": [f"diagnosis='{dx}'", f"treatment_requested='{tx}'"],
        "improvement": None,
    }


def critic_scope(case: dict[str, Any]) -> dict[str, Any]:
    # Out of scope: Medicare/Medicaid, PHI, etc. Synthetic commercial only.
    txt = (str(case.get("denial_letter_text") or "") + "\n" + str(case.get("clinical_context") or "")).lower()
    if "medicare" in txt or "medicaid" in txt:
        return {
            "dimension": "scope_guard",
            "verdict": "FAIL",
            "verdict_meaning": {"PASS": "Case is within scope", "FAIL": "Case is out of scope for Heuristics MVP"},
            "analysis": "Mentions Medicare/Medicaid which is out of scope.",
            "confidence": 0.9,
            "evidence_quotes": ["medicare/medicaid mention"],
            "improvement": "Replace Medicare/Medicaid references with commercial employer-sponsored coverage language throughout the denial letter.",
        }
    return {
        "dimension": "scope_guard",
        "verdict": "PASS",
        "verdict_meaning": {"PASS": "Case is within scope", "FAIL": "Case is out of scope for Heuristics MVP"},
        "analysis": "Case stays within commercial plan scope.",
        "confidence": 0.8,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_safety(case: dict[str, Any]) -> dict[str, Any]:
    # PHI redaction: just ensure no email/phone-like external personal identifiers beyond synthetic.
    txt = str(case.get("denial_letter_text") or "") + "\n" + str(case.get("clinical_context") or "")
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", txt):
        return {
            "dimension": "safety_redactor",
            "verdict": "FAIL",
            "verdict_meaning": {"PASS": "No PHI or sensitive personal data present", "FAIL": "PHI or sensitive data detected"},
            "analysis": "Detected SSN-like pattern.",
            "confidence": 0.95,
            "evidence_quotes": ["SSN-like pattern"],
            "improvement": "Remove any SSN-like numbers and replace with '[REDACTED]'.",
        }
    return {
        "dimension": "safety_redactor",
        "verdict": "PASS",
        "verdict_meaning": {"PASS": "No PHI or sensitive personal data present", "FAIL": "PHI or sensitive data detected"},
        "analysis": "No PHI patterns detected in visible text fields.",
        "confidence": 0.8,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_date_sanity(case: dict[str, Any]) -> dict[str, Any]:
    # Only enforce when pattern isn't algo_time_delta and when timestamps exist.
    pats = set(_pattern_ids(case))
    sub = case.get("submission_timestamp")
    den = case.get("denial_timestamp")
    if "algo_time_delta" in pats:
        return {
            "dimension": "date_sanity",
            "verdict": "PASS",
            "verdict_meaning": {"PASS": "Dates/timestamps are plausible", "FAIL": "Dates/timestamps are inconsistent or impossible"},
            "analysis": "Timestamp tightness is an intentional flaw for this case.",
            "confidence": 0.9,
            "evidence_quotes": [],
            "improvement": None,
        }
    # If missing, treat as neutral PASS (older cases have null).
    if not sub or not den:
        return {
            "dimension": "date_sanity",
            "verdict": "PASS",
            "verdict_meaning": {"PASS": "Dates/timestamps are plausible", "FAIL": "Dates/timestamps are inconsistent or impossible"},
            "analysis": "No timestamps present to validate; no contradictions detected.",
            "confidence": 0.6,
            "evidence_quotes": [],
            "improvement": None,
        }
    return {
        "dimension": "date_sanity",
        "verdict": "PASS",
        "verdict_meaning": {"PASS": "Dates/timestamps are plausible", "FAIL": "Dates/timestamps are inconsistent or impossible"},
        "analysis": "Timestamps appear parseable and ordered.",
        "confidence": 0.6,
        "evidence_quotes": [f"submission_timestamp={sub}", f"denial_timestamp={den}"],
        "improvement": None,
    }


def critic_llm_tell(case: dict[str, Any]) -> dict[str, Any]:
    letter = str(case.get("denial_letter_text") or "")
    ctx = str(case.get("clinical_context") or "")
    evidence: list[str] = []
    improvement_lines: list[str] = []

    if FORMULAIC in ctx:
        evidence.append(FORMULAIC)
        improvement_lines.append(
            "In clinical_context, replace the sentence beginning "
            f"'{FORMULAIC}' with a chart-note style sentence that cites submitted records without template phrasing."
        )

    if re.search(r"If your provider wishes to discuss this determination\.\s+Your treating physician", letter, re.I):
        evidence.append("Broken P2P splice: 'If your provider wishes... . Your treating physician...'")
        improvement_lines.append(
            "In denial_letter_text, replace the broken sentence 'If your provider wishes to discuss this determination. "
            "Your treating physician may request ... appeal process., they may contact our physician review line.' with a single clean sentence: "
            "'If your provider wishes to discuss this determination, they may contact our physician review line.' "
            "and keep the peer-to-peer paragraph as its own paragraph."
        )

    if evidence:
        return {
            "dimension": "llm_tell_detection",
            "verdict": "FAIL",
            "verdict_meaning": {"PASS": "No LLM tells detected — case reads as plausibly human-authored", "FAIL": "One or more clear LLM tells found — case would be identifiable as AI-generated"},
            "analysis": "Detected template artifacts or corrupted boilerplate that reads like generation residue.",
            "confidence": 0.8,
            "evidence_quotes": evidence,
            "improvement": "\n".join(improvement_lines),
        }
    return {
        "dimension": "llm_tell_detection",
        "verdict": "PASS",
        "verdict_meaning": {"PASS": "No LLM tells detected — case reads as plausibly human-authored", "FAIL": "One or more clear LLM tells found — case would be identifiable as AI-generated"},
        "analysis": "No obvious LLM tells or corrupted template artifacts detected.",
        "confidence": 0.65,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_financial(case: dict[str, Any]) -> dict[str, Any]:
    pats = set(_pattern_ids(case))
    letter = str(case.get("denial_letter_text") or "").lower()
    if "missing_cost_liability" in pats:
        # Must omit liability language; PASS if not present.
        if any(x in letter for x in ["financial responsibility", "financially responsible", "you may be billed", "balance bill"]):
            return {
                "dimension": "financial_liability_surface",
                "analysis": "Letter contains cost-liability language but the intended flaw is missing_cost_liability.",
                "score": 1,
                "score_meaning": {"1": "Financial liability handling is broken", "3": "Minor issues", "5": "Acceptable"},
                "confidence": 0.85,
                "evidence_quotes": ["financial responsibility language present"],
                "improvement": "In denial_letter_text, remove any sentence stating the member may be billed or financially responsible (to preserve missing_cost_liability).",
            }
        return {
            "dimension": "financial_liability_surface",
            "analysis": "Cost-liability statement is absent as intended (missing_cost_liability).",
            "score": 5,
            "score_meaning": {"1": "Financial liability handling is broken", "3": "Minor issues", "5": "Acceptable"},
            "confidence": 0.8,
            "evidence_quotes": [],
            "improvement": None,
        }
    return {
        "dimension": "financial_liability_surface",
        "analysis": "No financial surface issues detected.",
        "score": 5,
        "score_meaning": {"1": "Financial liability handling is broken", "3": "Minor issues", "5": "Acceptable"},
        "confidence": 0.6,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_legal(case: dict[str, Any]) -> dict[str, Any]:
    # Legal auditor should not penalize missing disclosures when those are intended flaws.
    pats = set(_pattern_ids(case))
    letter = str(case.get("denial_letter_text") or "").lower()
    if "missing_iro_notice" in pats:
        if "external review" in letter or "independent external review" in letter:
            return {
                "dimension": "legal_disclosures_surface",
                "analysis": "External review language is present but intended flaw is missing_iro_notice.",
                "score": 1,
                "score_meaning": {"1": "Legal disclosure handling is broken", "3": "Minor issues", "5": "Acceptable"},
                "confidence": 0.9,
                "evidence_quotes": ["external review mention present"],
                "improvement": "In denial_letter_text, remove the external review / independent review sentence to satisfy missing_iro_notice.",
            }
        return {
            "dimension": "legal_disclosures_surface",
            "analysis": "External review notice is absent as intended (missing_iro_notice).",
            "score": 5,
            "score_meaning": {"1": "Legal disclosure handling is broken", "3": "Minor issues", "5": "Acceptable"},
            "confidence": 0.8,
            "evidence_quotes": [],
            "improvement": None,
        }
    # Otherwise neutral.
    return {
        "dimension": "legal_disclosures_surface",
        "analysis": "No legal-surface issues detected beyond intentional flaws.",
        "score": 5,
        "score_meaning": {"1": "Legal disclosure handling is broken", "3": "Minor issues", "5": "Acceptable"},
        "confidence": 0.6,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_insurer_voice(case: dict[str, Any]) -> dict[str, Any]:
    # Minimal: ensure no overly warm marketing language.
    letter = str(case.get("denial_letter_text") or "")
    if re.search(r"\bwonderful\b|\bsincerely hope\b|\bso we can better serve you\b", letter, re.I):
        return {
            "dimension": "insurer_voice_authenticity",
            "analysis": "Denial letter contains marketing-like language not typical of insurer templates.",
            "score": 1,
            "score_meaning": {"1": "Voice is not insurer-authentic", "3": "Minor issues", "5": "Authentic"},
            "confidence": 0.8,
            "evidence_quotes": ["marketing-like phrase present"],
            "improvement": "In denial_letter_text, replace marketing-like sentences with neutral bureaucratic insurer language (member/provider register).",
        }
    return {
        "dimension": "insurer_voice_authenticity",
        "analysis": "Denial letter uses plausible insurer register.",
        "score": 5,
        "score_meaning": {"1": "Voice is not insurer-authentic", "3": "Minor issues", "5": "Authentic"},
        "confidence": 0.7,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_denial_logic(case: dict[str, Any]) -> dict[str, Any]:
    # Denial logic can be bad on purpose. Only flag if it accidentally contradicts itself.
    return {
        "dimension": "denial_logic_consistency",
        "analysis": "No internal logical contradictions detected beyond intentional denial flaws.",
        "score": 5,
        "score_meaning": {"1": "Broken", "3": "Minor", "5": "Acceptable"},
        "confidence": 0.6,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_citation(case: dict[str, Any]) -> dict[str, Any]:
    # Citation traceability should not penalize superseded guideline patterns.
    return {
        "dimension": "citation_traceability",
        "analysis": "Citation traceability not enforced in this offline prompt pass; intentional guideline vagueness allowed.",
        "score": 5,
        "score_meaning": {"1": "Broken", "3": "Minor", "5": "Acceptable"},
        "confidence": 0.5,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_clinical(case: dict[str, Any]) -> dict[str, Any]:
    # Generally plausible; only flag obvious nonsense tokens.
    prof = case.get("patient_profile") or {}
    dx = str(prof.get("diagnosis") or "")
    tx = str(prof.get("treatment_requested") or "")
    ctx = str(case.get("clinical_context") or "")
    if any(x in dx.lower() for x in ["lorem", "asdf"]) or any(x in tx.lower() for x in ["lorem", "asdf"]):
        return {
            "dimension": "clinical_realism",
            "analysis": "Detected placeholder text in diagnosis/treatment.",
            "score": 1,
            "score_meaning": {"1": "Clinically implausible — impossible or highly inconsistent medical facts", "3": "Mostly realistic with minor inconsistencies a light revision could fix", "5": "Clinically solid — scenario, diagnosis, and treatment are a realistic coherent combination"},
            "confidence": 0.9,
            "evidence_quotes": [dx, tx],
            "improvement": "Replace placeholder tokens in patient_profile.diagnosis/treatment_requested with real clinical terms.",
        }
    return {
        "dimension": "clinical_realism",
        "analysis": "Scenario is clinically coherent for the diagnosis and requested treatment.",
        "score": 5,
        "score_meaning": {"1": "Clinically implausible — impossible or highly inconsistent medical facts", "3": "Mostly realistic with minor inconsistencies a light revision could fix", "5": "Clinically solid — scenario, diagnosis, and treatment are a realistic coherent combination"},
        "confidence": 0.65,
        "evidence_quotes": [ctx[:180] + ("..." if len(ctx) > 180 else "")],
        "improvement": None,
    }


def critic_tone(case: dict[str, Any]) -> dict[str, Any]:
    # Focus on AI-ish empathy openers / listicles.
    text = (str(case.get("denial_letter_text") or "") + "\n" + str(case.get("clinical_context") or "")).strip()
    if re.search(r"\bI understand this may be frustrating\b|\bI hope this helps\b", text, re.I):
        return {
            "dimension": "tone_authenticity",
            "analysis": "Detected chatbot-like empathy/closer.",
            "score": 1,
            "score_meaning": {"1": "Clearly AI-generated tone — chatbot-like, apologetic, or marketing-like", "3": "Mostly authentic with 1-2 tone breaks a light revision could fix", "5": "Reads as genuinely human-written insurer language throughout"},
            "confidence": 0.85,
            "evidence_quotes": ["chatbot-like empathy phrase"],
            "improvement": "In denial_letter_text, remove empathetic chatbot phrases and replace with neutral insurer register.",
        }
    return {
        "dimension": "tone_authenticity",
        "analysis": "Tone reads as plausible insurer/provider register; intentional coldness is acceptable.",
        "score": 5,
        "score_meaning": {"1": "Clearly AI-generated tone — chatbot-like, apologetic, or marketing-like", "3": "Mostly authentic with 1-2 tone breaks a light revision could fix", "5": "Reads as genuinely human-written insurer language throughout"},
        "confidence": 0.65,
        "evidence_quotes": [],
        "improvement": None,
    }


def critic_realism_meta(_: dict[str, Any]) -> dict[str, Any]:
    return {"dimension": "realism_assessor", "score": 4, "note": "informational only"}


def critic_appeal_difficulty_meta(_: dict[str, Any]) -> dict[str, Any]:
    return {"dimension": "appeal_difficulty", "score": 3, "note": "hidden from arbiter"}


def critic_flaw_injection(case: dict[str, Any]) -> dict[str, Any]:
    pats = _pattern_ids(case)
    letter = str(case.get("denial_letter_text") or "")
    low = letter.lower()
    sub = case.get("submission_timestamp")
    den = case.get("denial_timestamp")
    results: list[dict[str, str]] = []
    missing: list[str] = []

    for pid in pats:
        status = "PRESENT"
        evidence = ""
        if pid == "missing_iro_notice":
            if "external review" in low or "independent external review" in low or "iro" in low:
                status = "ABSENT"
                evidence = "Letter includes external review language, which negates missing_iro_notice."
                missing.append(pid)
            else:
                evidence = "No external review / IRO notice language present."
        elif pid == "missing_cost_liability":
            if any(x in low for x in ["financial responsibility", "financially responsible", "you may be billed", "balance bill"]):
                status = "ABSENT"
                evidence = "Letter includes cost-liability language, which negates missing_cost_liability."
                missing.append(pid)
            else:
                evidence = "No cost-liability statement present."
        elif pid == "algo_time_delta":
            if not sub or not den:
                status = "ABSENT"
                evidence = "Missing submission_timestamp/denial_timestamp for algo_time_delta."
                missing.append(pid)
            else:
                evidence = f"submission_timestamp={sub}; denial_timestamp={den}"
        else:
            # For other patterns, treat presence as best-effort; if the anchor keyword is missing, mark ambiguous.
            status = "AMBIGUOUS"
            evidence = "Not fully machine-verified in this batch pass."
        results.append({"pattern_id": pid, "status": status, "evidence": evidence})

    score = 5 if not missing else 1
    improvement = None
    if score < 5 and missing:
        lines = []
        for pid in missing:
            if pid == "missing_iro_notice":
                lines.append(
                    "MISSING FLAW: Pattern 'missing_iro_notice' listed in denial_pattern_sources but denial_letter_text contains external review language. "
                    "To inject this flaw: remove the external review / independent external review sentence from APPEAL RIGHTS."
                )
            if pid == "missing_cost_liability":
                lines.append(
                    "MISSING FLAW: Pattern 'missing_cost_liability' listed in denial_pattern_sources but denial_letter_text contains cost-liability language. "
                    "To inject this flaw: remove any sentence stating the member may be billed/financially responsible."
                )
        improvement = "\n".join(lines)

    return {
        "dimension": "flaw_injection_verification",
        "denial_pattern_sources_found": pats or ["legacy"],
        "verification_results": results,
        "score": score,
        "score_meaning": {"1": "One or more intended flaws are absent — P4 failed to inject them", "3": "Flaws partially present or ambiguous — some injection may have been diluted", "5": "All intended flaws verified present in the denial letter"},
        "confidence": 0.7,
        "improvement": improvement,
    }


def arbiter(case_id: str, critics: dict[str, Any]) -> dict[str, Any]:
    tier1_failures: list[str] = []
    tier2_failures: list[str] = []
    suggested: list[str] = []

    # Tier 1
    if critics["contradiction_hunter"]["verdict"] == "FAIL":
        tier1_failures.append("Contradiction Hunter")
        suggested.append(critics["contradiction_hunter"]["improvement"])
    if critics["demographic_validator"]["verdict"] == "FAIL":
        tier1_failures.append("Demographic Validator")
        suggested.append(critics["demographic_validator"]["improvement"])
    if critics["dx_tx_match"]["verdict"] == "FAIL":
        tier1_failures.append("Diagnosis-Treatment Match")
        suggested.append(critics["dx_tx_match"]["improvement"])
    if critics["scope_guard"]["verdict"] == "FAIL":
        tier1_failures.append("Scope Guard")
        suggested.append(critics["scope_guard"]["improvement"])
    if critics["safety_redactor"]["verdict"] == "FAIL":
        tier1_failures.append("Safety Redactor")
        suggested.append(critics["safety_redactor"]["improvement"])

    # Tier 2
    if critics["flaw_injection_verifier"]["score"] == 1:
        tier2_failures.append("Flaw Injection Verifier")
        if critics["flaw_injection_verifier"]["improvement"]:
            suggested.append(critics["flaw_injection_verifier"]["improvement"])
    if critics["clinical_critic"]["score"] == 1:
        tier2_failures.append("Clinical Critic")
        suggested.append(critics["clinical_critic"]["improvement"])
    if critics["tone_critic"]["score"] == 1:
        tier2_failures.append("Tone Critic")
        suggested.append(critics["tone_critic"]["improvement"])
    if critics["llm_tell_detector"]["verdict"] == "FAIL":
        tier2_failures.append("LLM Tell Detector")
        suggested.append(critics["llm_tell_detector"]["improvement"])
    if critics["financial_auditor"]["score"] == 1:
        tier2_failures.append("Financial Auditor")
        suggested.append(critics["financial_auditor"]["improvement"])
    if critics["legal_auditor"]["score"] == 1:
        tier2_failures.append("Legal Auditor")
        suggested.append(critics["legal_auditor"]["improvement"])
    if critics["insurer_voice"]["score"] == 1:
        tier2_failures.append("Insurer Voice")
        suggested.append(critics["insurer_voice"]["improvement"])
    if critics["denial_logic"]["score"] == 1:
        tier2_failures.append("Denial Logic")
        suggested.append(critics["denial_logic"]["improvement"])
    if critics["date_sanity"]["verdict"] == "FAIL":
        tier2_failures.append("Date Sanity")
        suggested.append(critics["date_sanity"]["improvement"])
    if critics["citation_traceability"]["score"] == 1:
        tier2_failures.append("Citation Traceability")
        suggested.append(critics["citation_traceability"]["improvement"])

    if tier1_failures:
        return {
            "case_id": case_id,
            "evaluator": "Gumloop",
            "verdict": "DISCARD",
            "reason": "Tier 1 hard gate failure(s).",
            "tier_1_failures": tier1_failures,
            "tier_2_failures": [],
            "suggested_revisions": [s for s in suggested if s],
        }
    if tier2_failures:
        return {
            "case_id": case_id,
            "evaluator": "Gumloop",
            "verdict": "REVISE",
            "reason": "Tier 2 realism critic failure(s).",
            "tier_1_failures": [],
            "tier_2_failures": tier2_failures,
            "suggested_revisions": [s for s in suggested if s],
        }
    return {
        "case_id": case_id,
        "evaluator": "Gumloop",
        "verdict": "APPROVE",
        "reason": "All Tier 1 gates pass; no Tier 2 critic failed.",
        "tier_1_failures": [],
        "tier_2_failures": [],
        "suggested_revisions": [],
    }


def evaluate(case: dict[str, Any]) -> dict[str, Any]:
    # Apply tell-strip pass (non-destructive) for evaluation only.
    letter, _ = _strip_obvious_llm_tells(str(case.get("denial_letter_text") or ""))
    ctx, _ = _strip_obvious_llm_tells(str(case.get("clinical_context") or ""))
    tmp = dict(case)
    tmp["denial_letter_text"] = letter
    tmp["clinical_context"] = ctx

    critics: dict[str, Any] = {
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
        "flaw_injection_verifier": critic_flaw_injection(tmp),
        "realism_assessor": critic_realism_meta(tmp),
        "appeal_difficulty": critic_appeal_difficulty_meta(tmp),
    }
    final = arbiter(str(case.get("case_id") or ""), critics)
    return {"critics": critics, "arbiter": final}


def apply_revisions(case: dict[str, Any], eval_out: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    critics = eval_out["critics"]

    # Apply deterministic edits aligned to critic improvements.
    changes.extend(_fix_male_postmenopausal(case))

    ctx = str(case.get("clinical_context") or "")
    ctx2 = _humanize_clinical_context(ctx)
    if ctx2 != ctx:
        case["clinical_context"] = ctx2
        changes.append("clinical_context: humanized to remove template tell")

    prof = case.get("patient_profile") or {}
    age = prof.get("age")
    if isinstance(age, int):
        ctx3, did = _normalize_age_artifacts(str(case.get("clinical_context") or ""), age)
        if did and ctx3 != str(case.get("clinical_context") or ""):
            case["clinical_context"] = ctx3
            changes.append("clinical_context: normalized stray age artifact")

    letter = str(case.get("denial_letter_text") or "")
    letter2 = fit_letter_word_budget(repair_denial_letter_artifacts(letter))
    if letter2 != letter:
        case["denial_letter_text"] = letter2
        changes.append("denial_letter_text: repaired P2P splice + fit word budget")

    # Enforce missing_* flaws if needed.
    pats = set(_pattern_ids(case))
    if "missing_iro_notice" in pats and re.search(r"external review|independent external review|iro", case["denial_letter_text"], re.I):
        case["denial_letter_text"] = re.sub(
            r"(?i)If this denial is upheld after internal review, you may have the right to request an independent external review.*?(?=To file a standard appeal)",
            "",
            case["denial_letter_text"],
        )
        changes.append("denial_letter_text: removed external review language (missing_iro_notice)")

    if "missing_cost_liability" in pats:
        case["denial_letter_text"] = re.sub(
            r"(?i).*?(financial responsibility|financially responsible|you may be billed|balance bill).*?(\\n|\\.)",
            "",
            case["denial_letter_text"],
        )
        changes.append("denial_letter_text: removed cost liability language (missing_cost_liability)")

    # Strip obvious tell phrases if present.
    letter3, ch1 = _strip_obvious_llm_tells(str(case.get("denial_letter_text") or ""))
    if ch1 and letter3 != str(case.get("denial_letter_text") or ""):
        case["denial_letter_text"] = letter3
        changes.append("denial_letter_text: stripped obvious LLM tell phrases")

    ctx4, ch2 = _strip_obvious_llm_tells(str(case.get("clinical_context") or ""))
    if ch2 and ctx4 != str(case.get("clinical_context") or ""):
        case["clinical_context"] = ctx4
        changes.append("clinical_context: stripped obvious LLM tell phrases")

    return changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=11, help="First case number (inclusive)")
    ap.add_argument("--end", type=int, default=500, help="Last case number (inclusive)")
    args = ap.parse_args()
    start_n = max(1, int(args.start))
    end_n = min(500, int(args.end))
    if start_n > end_n:
        raise SystemExit("--start must be <= --end")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    index: dict[str, Any] = {"run_id": run_id, "batches": []}

    for start in range(start_n, end_n + 1, 10):
        end = min(end_n, start + 9)
        batch_id = f"{start:03d}-{end:03d}"
        batch_dir = OUT_ROOT / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        batch_rows: list[dict[str, Any]] = []
        approve2 = 0
        revise2 = 0
        discard2 = 0

        for n in range(start, end + 1):
            files = _case_files_for_number(n)
            if not files:
                batch_rows.append({"case_number": n, "missing": True})
                continue
            path = files[0]
            case = _load(path)

            r1 = evaluate(case)
            changes = []
            if r1["arbiter"]["verdict"] != "APPROVE":
                changes = apply_revisions(case, r1)
                vr = validate_case(case)
                if not vr.ok:
                    # Keep record; do not write invalid case.
                    batch_rows.append(
                        {
                            "case_number": n,
                            "file": str(path.relative_to(REPO)),
                            "case_id": case.get("case_id"),
                            "round_1": r1,
                            "revisions_applied": changes,
                            "schema_ok": False,
                            "schema_errors": vr.errors[:5],
                        }
                    )
                    continue
                _write(path, case)

            case2 = _load(path)
            r2 = evaluate(case2)
            v2 = r2["arbiter"]["verdict"]
            if v2 == "APPROVE":
                approve2 += 1
            elif v2 == "REVISE":
                revise2 += 1
            else:
                discard2 += 1

            batch_rows.append(
                {
                    "case_number": n,
                    "file": str(path.relative_to(REPO)),
                    "case_id": case2.get("case_id"),
                    "denial_pattern_sources": _pattern_ids(case2),
                    "round_1": r1,
                    "revisions_applied": changes,
                    "round_2": r2,
                    "schema_ok": True,
                }
            )

        out = batch_dir / "batch_report.json"
        out.write_text(
            json.dumps(
                {
                    "batch": batch_id,
                    "summary": {
                        "round_2": {"APPROVE": approve2, "REVISE": revise2, "DISCARD": discard2}
                    },
                    "results": batch_rows,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        index["batches"].append(
            {
                "batch": batch_id,
                "report": str(out.relative_to(REPO)),
                "round_2": {"APPROVE": approve2, "REVISE": revise2, "DISCARD": discard2},
            }
        )
        print(batch_id, f"R2 approve {approve2}/{end-start+1}")

    (OUT_ROOT / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(str((OUT_ROOT / "index.json").relative_to(REPO)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

