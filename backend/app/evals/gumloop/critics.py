from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.case_generator.safety import scan_banned, scan_phi

from .types import FlawInjectionResult, FlawInjectionVerifierOutput, PassFailCriticOutput, ScoreCriticOutput


_LLM_TELL_PHRASES = [
    "it's important to note that",
    "i understand this may be frustrating",
    "i hope this helps",
    "certainly!",
    "of course!",
    "firstly",
    "secondly",
    "finally",
    "in conclusion",
    "with this in mind",
    "building on the above",
]

_INSURANCE_OUT_OF_SCOPE = [
    "medicare",
    "medicaid",
    "chip",
    "workers' compensation",
    "workers compensation",
    "tricare",
    "va benefits",
]

_COST_LIABILITY_MARKERS = [
    "financially responsible",
    "financial responsibility",
    "you will be responsible",
    "you may be responsible",
    "balance bill",
    "you may be billed",
]

_EXTERNAL_REVIEW_MARKERS = [
    "external review",
    "independent external review",
    "iro",
    "independent review organization",
]


def _lower(x: Any) -> str:
    return (x or "").lower()


def safety_redactor(case: dict[str, Any]) -> PassFailCriticOutput:
    text = "\n".join(
        [
            str(case.get("denial_letter_text") or ""),
            str(case.get("clinical_context") or ""),
        ]
    )
    phi = scan_phi(text)
    banned = scan_banned(text)
    verdict: str = "PASS" if not (phi or banned) else "FAIL"
    phi_findings = ["none"] if not phi else ["Potential PHI detected by scanner."]
    safety_findings = ["none"] if not banned else ["Banned-topic language detected by scanner."]
    improvement = None
    if verdict == "FAIL":
        if phi:
            improvement = (
                "PHI FOUND: In denial_letter_text/clinical_context, content matched PHI detector. "
                "Fix: replace any specific names/IDs/addresses/phones with safe placeholders (e.g., 'Member ID: #####')."
            )
        if banned:
            improvement = (
                (improvement + "\n" if improvement else "")
                + "SAFETY VIOLATION: In denial_letter_text/clinical_context, content matched banned-topic filter. "
                "Fix: remove inflammatory/vigilantism language; replace with neutral clinical/procedural phrasing."
            )
    return {
        "dimension": "safety_redaction",
        "verdict": verdict,  # type: ignore[typeddict-item]
        "verdict_meaning": {
            "PASS": "Case is synthetic, safe, and professionally neutral",
            "FAIL": "Case contains real PHI, real identifying information, or prohibited inflammatory content",
        },
        "phi_findings": phi_findings,
        "safety_findings": safety_findings,
        "analysis": "Deterministic PHI + banned-topic scan over denial letter and clinical context.",
        "confidence": 0.9,
        "improvement": improvement,
    }


def scope_guard(case: dict[str, Any]) -> PassFailCriticOutput:
    hay = " ".join(
        [
            str(case.get("insurer") or ""),
            str(case.get("denial_letter_text") or ""),
            str(case.get("clinical_context") or ""),
        ]
    ).lower()
    oos = next((m for m in _INSURANCE_OUT_OF_SCOPE if m in hay), None)
    verdict = "FAIL" if oos else "PASS"
    improvement = None
    if verdict == "FAIL":
        improvement = (
            f"The case is out of scope because text contains '{oos}'. Fix: rewrite the coverage framing as a "
            "US commercial health plan (employer-sponsored or ACA individual market) and remove Medicare/Medicaid/etc."
        )
    return {
        "dimension": "scope_guard",
        "verdict": verdict,  # type: ignore[typeddict-item]
        "verdict_meaning": {
            "PASS": "Case is a US commercial health insurance denial — within scope",
            "FAIL": "Case involves Medicare, Medicaid, workers comp, or other out-of-scope insurance type",
        },
        "analysis": "Checks for out-of-scope insurance keywords across letter/context.",
        "confidence": 0.85,
        "evidence_quotes": [oos] if oos else [],
        "improvement": improvement,
    }


def demographic_validator(case: dict[str, Any]) -> PassFailCriticOutput:
    prof = case.get("patient_profile") or {}
    age = prof.get("age")
    gender = str(prof.get("gender") or "")
    ok = isinstance(age, int) and 0 < age < 110 and gender in {"F", "M", "X", "U"}
    verdict = "PASS" if ok else "FAIL"
    improvement = None
    if verdict == "FAIL":
        improvement = (
            "In patient_profile, age or gender is invalid. Fix: set age to an integer 1–109 and gender to one of "
            "['F','M','X','U'] and ensure clinical_context matches."
        )
    return {
        "dimension": "demographic_validator",
        "verdict": verdict,  # type: ignore[typeddict-item]
        "verdict_meaning": {"PASS": "Demographics are plausible and internally consistent", "FAIL": "Broken demographics"},
        "analysis": "Validates age range + allowed gender codes.",
        "confidence": 0.9,
        "evidence_quotes": [f"age={age}", f"gender={gender}"],
        "improvement": improvement,
    }


def diagnosis_treatment_match(case: dict[str, Any]) -> PassFailCriticOutput:
    prof = case.get("patient_profile") or {}
    dx = str(prof.get("diagnosis") or "").strip()
    tx = str(prof.get("treatment_requested") or "").strip()
    verdict = "PASS" if (dx and tx) else "FAIL"
    improvement = None
    if verdict == "FAIL":
        improvement = (
            f"The treatment '{tx or '<missing>'}' has no recognised clinical application for '{dx or '<missing>'}'. "
            "Fix one of these: set a non-empty diagnosis and treatment_requested that plausibly match."
        )
    return {
        "dimension": "diagnosis_treatment_match",
        "verdict": verdict,  # type: ignore[typeddict-item]
        "verdict_meaning": {
            "PASS": "Treatment is a plausible intervention for this diagnosis",
            "FAIL": "Treatment has no clinical relationship to the diagnosis — likely a hallucination",
        },
        "analysis": "Hard gate: requires non-empty diagnosis + treatment.",
        "confidence": 0.7,
        "evidence_quotes": [dx, tx],
        "improvement": improvement,
    }


def contradiction_hunter(case: dict[str, Any]) -> PassFailCriticOutput:
    prof = case.get("patient_profile") or {}
    dx = str(prof.get("diagnosis") or "")
    tx = str(prof.get("treatment_requested") or "")
    letter = str(case.get("denial_letter_text") or "")
    ctx = str(case.get("clinical_context") or "")

    missing = []
    if dx and dx.split("(")[0].strip() and dx.split("(")[0].strip() not in letter and dx.split("(")[0].strip() not in ctx:
        missing.append("diagnosis")
    if tx and tx not in letter and tx not in ctx:
        missing.append("treatment_requested")

    verdict = "FAIL" if missing else "PASS"
    improvement = None
    if verdict == "FAIL":
        improvement = (
            "CONTRADICTION: patient_profile diagnosis/treatment are not reflected in denial_letter_text/clinical_context. "
            f"Missing mentions: {', '.join(missing)}. Fix: rewrite denial_letter_text opening summary and clinical_context "
            "to explicitly name the requested service and diagnosis from patient_profile."
        )
    return {
        "dimension": "internal_contradiction",
        "verdict": verdict,  # type: ignore[typeddict-item]
        "verdict_meaning": {
            "PASS": "Core facts are stable across all documents",
            "FAIL": "Core facts are broken — documents describe different patients or procedures",
        },
        "analysis": "Checks that patient_profile diagnosis/treatment are echoed in letter/context.",
        "confidence": 0.7,
        "evidence_quotes": [dx, tx],
        "improvement": improvement,
    }


def llm_tell_detector(case: dict[str, Any]) -> PassFailCriticOutput:
    letter = _lower(case.get("denial_letter_text"))
    ctx = _lower(case.get("clinical_context"))
    hits: list[tuple[str, str]] = []

    for p in _LLM_TELL_PHRASES:
        if p in letter:
            hits.append(("denial_letter_text", p))
        if p in ctx:
            hits.append(("clinical_context", p))

    verdict = "FAIL" if hits else "PASS"
    improvements: list[str] = []
    for field, phrase in hits[:6]:
        improvements.append(
            f"In {field}, replace '{phrase}' with ''. Reason: the phrase is a recognizable LLM tell (performative/essay-like transition)."
        )
    improvement = None if verdict == "PASS" else "\n".join(improvements)
    return {
        "dimension": "llm_tell_detection",
        "verdict": verdict,  # type: ignore[typeddict-item]
        "verdict_meaning": {
            "PASS": "No LLM tells detected — case reads as plausibly human-authored",
            "FAIL": "One or more clear LLM tells found — case would be identifiable as AI-generated",
        },
        "analysis": "Scans for known LLM-tell phrases in denial letter and clinical context.",
        "confidence": 0.75,
        "evidence_quotes": [f"{f}:{p}" for f, p in hits],
        "improvement": improvement,
    }


def flaw_injection_verifier(case: dict[str, Any]) -> FlawInjectionVerifierOutput:
    sources = case.get("denial_pattern_sources") or []
    denial = str(case.get("denial_letter_text") or "")
    denial_l = denial.lower()

    # The corpus sometimes stores strings like "pattern_id: explanation...".
    pattern_ids: list[str] = []
    for s in sources:
        if not s:
            continue
        pid = str(s).split(":", 1)[0].strip()
        if pid:
            pattern_ids.append(pid)

    if not pattern_ids or all(p.lower() in {"legacy", "legacy manual generation"} for p in pattern_ids):
        return {
            "dimension": "flaw_injection_verification",
            "denial_pattern_sources_found": ["legacy"],
            "verification_results": [],
            "score": 3,
            "score_meaning": {
                "1": "One or more intended flaws are absent — P4 failed to inject them",
                "3": "Flaws partially present or ambiguous — some injection may have been diluted",
                "5": "All intended flaws verified present in the denial letter",
            },
            "confidence": 0.6,
            "improvement": None,
        }

    results: list[FlawInjectionResult] = []
    missing: list[str] = []

    for pid in pattern_ids:
        status: str = "AMBIGUOUS"
        evidence = ""

        if pid == "missing_cost_liability":
            has_cost = any(m in denial_l for m in _COST_LIABILITY_MARKERS)
            status = "PRESENT" if not has_cost else "ABSENT"
            evidence = "No cost-liability language found." if not has_cost else "Found cost-liability language."
        elif pid == "missing_iro_notice":
            has_iro = any(m in denial_l for m in _EXTERNAL_REVIEW_MARKERS)
            status = "PRESENT" if not has_iro else "ABSENT"
            evidence = "No external review language found." if not has_iro else "Found external review / IRO language."
        elif pid == "algo_time_delta":
            sub = case.get("submission_timestamp")
            den = case.get("denial_timestamp")
            if sub and den:
                try:
                    dt_sub = datetime.fromisoformat(str(sub).replace("Z", "+00:00"))
                    dt_den = datetime.fromisoformat(str(den).replace("Z", "+00:00"))
                    mins = abs((dt_den - dt_sub).total_seconds()) / 60.0
                    status = "PRESENT" if 1.0 <= mins <= 5.0 else "ABSENT"
                    evidence = f"submission={sub} denial={den} delta_minutes={mins:.2f}"
                except Exception:
                    status = "AMBIGUOUS"
                    evidence = f"Could not parse timestamps submission={sub} denial={den}"
            else:
                status = "AMBIGUOUS"
                evidence = "submission_timestamp or denial_timestamp missing."
        elif pid == "circular_medical_necessity":
            # Very rough: look for "not medically necessary" + "does not meet medical necessity criteria".
            status = "PRESENT" if re.search(r"not medically necessary.*meet medical necessity", denial_l, re.S) else "ABSENT"
            evidence = "Matched circular 'not medically necessary...meet medical necessity' phrasing." if status == "PRESENT" else "No circular phrasing match."
        else:
            # Unknown patterns are treated as ambiguous (we won't hard-fail offline).
            status = "AMBIGUOUS"
            evidence = "Pattern verifier does not implement this pattern offline."

        results.append({"pattern_id": pid, "status": status, "evidence": evidence})  # type: ignore[typeddict-item]
        if status == "ABSENT":
            missing.append(pid)

    score: int
    improvement: str | None
    if missing:
        score = 1
        improvement_lines = []
        for pid in missing:
            if pid == "missing_cost_liability":
                improvement_lines.append(
                    "MISSING FLAW: Pattern 'missing_cost_liability' listed in denial_pattern_sources but denial_letter_text contains cost-liability language. "
                    "To inject this flaw: remove any sentence stating the member may be billed or financially responsible for the denied service."
                )
            elif pid == "missing_iro_notice":
                improvement_lines.append(
                    "MISSING FLAW: Pattern 'missing_iro_notice' listed in denial_pattern_sources but denial_letter_text mentions external review/IRO. "
                    "To inject this flaw: remove external review/IRO language so the letter only describes internal appeal."
                )
            elif pid == "algo_time_delta":
                improvement_lines.append(
                    "MISSING FLAW: Pattern 'algo_time_delta' listed in denial_pattern_sources but timestamps are not 1–5 minutes apart. "
                    "To inject this flaw: set denial_timestamp to 1–5 minutes after submission_timestamp."
                )
            else:
                improvement_lines.append(
                    f"MISSING FLAW: Pattern '{pid}' listed in denial_pattern_sources but not detected. "
                    "To inject this flaw: modify denial_letter_text (or timestamps) so the pattern is clearly present."
                )
        improvement = "\n".join(improvement_lines)
    else:
        score = 5 if all(r["status"] in {"PRESENT", "AMBIGUOUS"} for r in results) else 3
        improvement = None if score == 5 else "Some intended flaws are ambiguous under offline detection; review manually."

    return {
        "dimension": "flaw_injection_verification",
        "denial_pattern_sources_found": pattern_ids,
        "verification_results": results,
        "score": score,  # type: ignore[typeddict-item]
        "score_meaning": {
            "1": "One or more intended flaws are absent — P4 failed to inject them",
            "3": "Flaws partially present or ambiguous — some injection may have been diluted",
            "5": "All intended flaws verified present in the denial letter",
        },
        "confidence": 0.65,
        "improvement": improvement,
    }


def clinical_critic(case: dict[str, Any]) -> ScoreCriticOutput:
    # Offline proxy: ensure basic clinical context includes at least one objective datum.
    ctx = str(case.get("clinical_context") or "")
    has_number = bool(re.search(r"\b\d+(\.\d+)?\b", ctx))
    score = 5 if has_number else 3
    improvement = None
    if score < 5:
        improvement = (
            "In clinical_context, add one objective clinical datum (e.g., lab value, imaging finding, scale score, "
            "or dated symptom severity) that supports the diagnosis/treatment request."
        )
    return {
        "dimension": "clinical_realism",
        "analysis": "Offline proxy check for objective clinical detail (numbers/labs/scores) in clinical_context.",
        "score": score,
        "score_meaning": {
            "1": "Clinically implausible — impossible or highly inconsistent medical facts",
            "3": "Mostly realistic with minor inconsistencies a light revision could fix",
            "5": "Clinically solid — scenario, diagnosis, and treatment are a realistic coherent combination",
        },
        "confidence": 0.55,
        "evidence_quotes": [ctx[:180]] if ctx else [],
        "improvement": improvement,
    }


def tone_critic(case: dict[str, Any]) -> ScoreCriticOutput:
    letter = _lower(case.get("denial_letter_text"))
    # Penalize empathetic/marketing language; insurer should be bureaucratic.
    bad = any(p in letter for p in ["we understand", "we're sorry", "hope this helps", "thank you for choosing"])
    score = 3 if bad else 5
    improvement = None
    if bad:
        improvement = (
            "In denial_letter_text, remove empathetic/marketing phrasing (e.g., 'we understand' / 'we're sorry'). "
            "Replace with neutral procedural language typical of denial templates."
        )
    return {
        "dimension": "overall_tone",
        "analysis": "Checks for empathetic/marketing language that reads unlike insurer templates.",
        "score": score,
        "score_meaning": {  # not in prompt, but consistent
            "1": "Tone is implausible for an insurer denial",
            "3": "Mostly bureaucratic with minor tone issues",
            "5": "Cold, procedural insurer voice",
        },
        "confidence": 0.6,
        "evidence_quotes": [],
        "improvement": improvement,
    }

