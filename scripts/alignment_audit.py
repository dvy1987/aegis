#!/usr/bin/env python3
"""Training-data alignment audit + deterministic fixes for synthetic denial cases.

Scope: eval/cases/drafts/case_*.json

Highest-priority concern: the injected flaw (metadata) must be *discoverable* by a
student that only sees `denial_letter_text` + `clinical_context`, and must match what
the teacher grading packet exposes to the judges. A second, equally damaging class is
**leakage**: internal generator tokens (sub_tactic / pattern ids / prompt scaffolding)
bleeding into student-visible text, which both breaks insurer voice and hands the
student the answer key.

This module does the *deterministic* half (free, surgical, reproducible):
  - detect + fix the `sub_tactic` template leak in denial_letter_text / clinical_context
  - flag structural issues for the LLM pass (algo_time_delta student-visibility, etc.)
  - basic PHI / date-sanity / internal-consistency checks

The semantic half (real flaw discoverability, subtle prompt bleed, contradictions) is
handled by the LLM critic pass and merged separately.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DRAFTS = REPO / "eval" / "cases" / "drafts"

SUB_TACTICS = [
    "missing_peer_to_peer", "step_therapy_missing", "modality_substitution",
    "conservative_treatment_required", "level_of_care_too_high", "visit_limit_exceeded",
    "formulary_tier_dispute", "frequency_excessive", "out_of_network_no_authorization",
    "guideline_mis_cite", "duration_excessive", "emergency_retroactive_auth",
    "not_evidence_based", "continuation_of_care_lapsed",
]
PATTERN_IDS = [
    "step_therapy_vague_mcg", "missing_erisa_disclosures", "missing_cost_liability",
    "missing_iro_notice", "timeline_violation", "wrong_appeals_contact",
    "circular_medical_necessity", "incorrect_demographic_guideline", "ignored_physician_letter",
    "superseded_guideline", "contraindication_to_step_therapy", "non_specialist_reviewer",
    "mhpaea_visit_limit_asymmetry", "mhpaea_step_therapy_asymmetry", "mhpaea_level_of_care_asymmetry",
    "experimental_despite_fda_approval", "wrong_benefit_category",
    "plan_exclusion_overrides_state_mandate", "unreasonable_documentation_deadline",
    "appeal_closed_as_withdrawn", "peer_to_peer_window_verbal_only", "algo_time_delta",
    "algo_boilerplate_fingerprint", "algo_reviewer_no_credentials",
]

# Spaced natural-language forms of internal tokens that should NEVER appear in prose.
_SPACED = {t.replace("_", " "): t for t in SUB_TACTICS + PATTERN_IDS}
# A couple of tokens render with the word expanded ("auth" -> "authorization").
_SPACED["emergency retroactive authorization"] = "emergency_retroactive_auth"
_SPACED["out of network no authorisation"] = "out_of_network_no_authorization"


def case_number(path: Path) -> int:
    return int(re.search(r"case_(\d+)_", path.name).group(1))


def _strip_subtactic_leak(text: str) -> tuple[str, list[str]]:
    """Remove a leaked spaced sub_tactic that trails 'requirements associated with/for'.

    Surgical: only the leaked clause is removed; any preceding legitimate content
    (e.g. a vague 'MCG Care Guidelines (edition not specified)' flaw) is preserved.
    Returns (new_text, list_of_removed_tokens).
    """
    removed: list[str] = []
    new = text
    for phrase, token in sorted(_SPACED.items(), key=lambda kv: -len(kv[0])):
        # match '... requirements associated with <phrase>' or '... requirements for <phrase>'
        pat = re.compile(
            r"(requirements)\s+(?:associated with|for)\s+" + re.escape(phrase)
            + r"(?=[.,;])",
            re.IGNORECASE,
        )
        if pat.search(new):
            new = pat.sub(r"\1", new)
            removed.append(token)
    return new, removed


_CLINICAL_PROSUPPORT = re.compile(
    r"Submitted documentation supports medical necessity for .*? in the setting of [^;]*?;\s*",
    re.IGNORECASE,
)
_CLINICAL_METACOMMENT = re.compile(
    r"(?:;\s*)?the denial letter does not discuss those records or cite the objective findings in the file\.?",
    re.IGNORECASE,
)


def _strip_clinical_editorial(text: str) -> tuple[str, bool]:
    """Remove the templated answer-key tail from clinical_context.

    Two leaked clauses are removed while any genuine clinical content between them
    (e.g. 'rule out cord injury (S13.4XXA)') is preserved:
      1. pro-patient conclusion: 'Submitted documentation supports medical necessity for ...'
      2. meta-commentary: '... the denial letter does not discuss those records ...'
    """
    had_leak = bool(_CLINICAL_PROSUPPORT.search(text) or _CLINICAL_METACOMMENT.search(text))
    new = _CLINICAL_PROSUPPORT.sub("", text)
    new = _CLINICAL_METACOMMENT.sub("", new)
    new = re.sub(r"\s{2,}", " ", new).strip()
    new = re.sub(r"\s+\.", ".", new)
    if new and not new.endswith((".", "?", "!")):
        new += "."
    # only report a change when an actual leak clause was removed (ignore whitespace-only)
    return (new if had_leak else text), had_leak


def _residual_token_leaks(text: str) -> list[str]:
    """Any spaced internal token still present anywhere in the text (belt and braces)."""
    low = text.lower()
    return sorted({tok for phr, tok in _SPACED.items() if phr in low})


_PHI = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "phone": re.compile(r"\b\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b"),
}


def _expected_anchors(case: dict[str, Any]) -> list[str]:
    prov = case.get("synthetic_provenance", {}) or {}
    diff = prov.get("appeal_difficulty", {}) or {}
    out: list[str] = []
    for w in diff.get("exploitable_weaknesses", []) or []:
        m = re.match(r"\s*Pattern anchor:\s*(.+)", w)
        if m:
            out.append(m.group(1).strip())
    for s in case.get("denial_pattern_sources", []) or []:
        out.append(s.split(":", 1)[0].strip())
    return sorted(set(out))


def audit_case(path: Path) -> dict[str, Any]:
    case = json.loads(path.read_text(encoding="utf-8"))
    letter = case.get("denial_letter_text", "") or ""
    clinical = case.get("clinical_context", "") or ""
    anchors = _expected_anchors(case)
    mc = (case.get("synthetic_provenance", {}) or {}).get("matrix_cell", {}) or {}

    fixed_letter, removed_l = _strip_subtactic_leak(letter)
    fixed_clinical, removed_c = _strip_subtactic_leak(clinical)
    fixed_clinical, clin_editorial = _strip_clinical_editorial(fixed_clinical)

    issues: list[dict[str, Any]] = []
    if removed_l:
        issues.append({"type": "subtactic_leak_letter", "severity": "high", "tokens": removed_l})
    if removed_c:
        issues.append({"type": "subtactic_leak_clinical", "severity": "high", "tokens": removed_c})
    if clin_editorial:
        issues.append({"type": "clinical_editorial_leak", "severity": "high"})

    residual = _residual_token_leaks(fixed_letter) + _residual_token_leaks(fixed_clinical)
    if residual:
        issues.append({"type": "residual_token_leak", "severity": "high", "tokens": sorted(set(residual))})

    # algo_time_delta: judge expects a 1-5 min turnaround; student only sees the letter,
    # so the fast timing must be visible in prose, not just in top-level timestamps.
    if "algo_time_delta" in anchors:
        prose_has_timing = bool(re.search(
            r"\b\d{1,2}:\d{2}\b|within (?:\d+ |a few )?(?:minute|hour)|minutes?\b|same[- ]day"
            r"|on the (?:same )?date the request was received|hours of receipt"
            r"|completed (?:on )?the (?:same )?(?:day|date)", letter, re.I))
        if not prose_has_timing:
            issues.append({"type": "algo_time_delta_not_student_visible", "severity": "high",
                           "note": "timestamps exist in metadata but turnaround speed is absent from letter prose"})

    # PHI (ignore fictional 555 numbers and toll-free insurer contact lines — never patient PHI)
    _TOLLFREE = ("800", "888", "877", "866", "855", "844", "833")

    def _real_phi(rx: re.Pattern, text: str) -> bool:
        for m in rx.finditer(text):
            norm = m.group(0).replace(" ", "-").replace(".", "-").lstrip("(").replace(")", "-")
            digits = re.sub(r"\D", "", norm)
            if "555" in digits[3:7]:  # any 555-xxxx exchange = fictional
                continue
            if digits[:3] in _TOLLFREE:  # toll-free = insurer contact, not patient PHI
                continue
            return True
        return False

    for kind, rx in _PHI.items():
        if _real_phi(rx, letter) or _real_phi(rx, clinical):
            issues.append({"type": f"phi_{kind}", "severity": "high"})

    # internal consistency: matrix sub_tactic should map to an anchor family (informational)
    if mc.get("sub_tactic") in (None, "", "unknown"):
        issues.append({"type": "matrix_subtactic_unknown", "severity": "med"})

    return {
        "case_id": case.get("case_id"),
        "path": str(path),
        "anchors": anchors,
        "sub_tactic": mc.get("sub_tactic"),
        "issues": issues,
        "_fixed_letter": fixed_letter,
        "_fixed_clinical": fixed_clinical,
        "_changed": bool(removed_l or removed_c or clin_editorial),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=100)
    ap.add_argument("--apply", action="store_true", help="write deterministic fixes in place")
    ap.add_argument("--report", type=str, default="")
    args = ap.parse_args()

    paths = sorted(
        (p for p in DRAFTS.glob("case_*.json") if args.start <= case_number(p) <= args.end),
        key=case_number,
    )
    results = [audit_case(p) for p in paths]

    n_changed = 0
    for r in results:
        if args.apply and r["_changed"]:
            # Apply as a raw-string replacement of the JSON-escaped field value so the
            # rest of the file (incl. any compact/idiosyncratic formatting) is preserved
            # byte-for-byte. Only the edited string value changes.
            path = Path(r["path"])
            raw = path.read_text(encoding="utf-8")
            case = json.loads(raw)
            for field, new_val in (("denial_letter_text", r["_fixed_letter"]),
                                   ("clinical_context", r["_fixed_clinical"])):
                old_val = case.get(field, "")
                if old_val == new_val:
                    continue
                esc_old = json.dumps(old_val, ensure_ascii=True)[1:-1]
                esc_new = json.dumps(new_val, ensure_ascii=True)[1:-1]
                if esc_old not in raw:
                    raise RuntimeError(f"{path.name}: could not locate {field} value for in-place edit")
                raw = raw.replace(esc_old, esc_new, 1)
            path.write_text(raw, encoding="utf-8")
            n_changed += 1

    # summary
    from collections import Counter
    counter: Counter = Counter()
    for r in results:
        for iss in r["issues"]:
            counter[iss["type"]] += 1
    print(f"audited cases {args.start}-{args.end}  ({len(results)} files)")
    print(f"deterministic fixes {'APPLIED to' if args.apply else 'PENDING for'} {sum(r['_changed'] for r in results)} files"
          + (f" (wrote {n_changed})" if args.apply else ""))
    print("\nissue counts:")
    for k, v in counter.most_common():
        print(f"  {v:4d}  {k}")

    if args.report:
        slim = [{k: v for k, v in r.items() if not k.startswith("_")} for r in results]
        Path(args.report).write_text(json.dumps(slim, indent=2), encoding="utf-8")
        print(f"\nreport -> {args.report}")


if __name__ == "__main__":
    main()
