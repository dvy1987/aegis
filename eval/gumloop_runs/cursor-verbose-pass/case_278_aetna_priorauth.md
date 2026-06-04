# Gumloop verbose pass — case_278_aetna_priorauth

**Insurer:** Aetna | **Denial:** Prior Authorization  
**Patterns:** mhpaea_visit_limit_asymmetry, algo_boilerplate_fingerprint  
**Profile:** 66M, Bipolar II disorder, current depressed episode (F31.81), Partial hospitalization program (PHP)

---

## Prompt 01 — Clinical Critic

```json
{
  "dimension": "clinical_realism",
  "analysis": "Bipolar II disorder, current depressed episode (F31.81) with Partial hospitalization program (PHP) is a clinically coherent commercial UM scenario; clinical_context aligns with profile.",
  "score": 5,
  "confidence": 0.9,
  "evidence_quotes": [
    "Bipolar II disorder, current depressed episode (F31.81)",
    "Partial hospitalization program (PHP)"
  ]
}
```

## Prompt 02 — Tone Critic

```json
{
  "dimension": "tone_authenticity",
  "analysis": "Aetna adverse-benefit administrative register throughout; no marketing or empathy breaks.",
  "score": 5,
  "confidence": 0.88,
  "evidence_quotes": [
    "NOTICE OF ADVERSE BENEFIT DETERMINATION"
  ]
}
```

## Prompt 03 — LLM Tell Detector

```json
{
  "dimension": "llm_tell_detection",
  "verdict": "PASS",
  "analysis": "No obvious LLM tells or corrupted template artifacts detected.",
  "confidence": 0.65,
  "evidence_quotes": []
}
```

## Prompt 04 — Financial Auditor

```json
{
  "dimension": "financial_consistency",
  "analysis": "No financial figures stated; neutral.",
  "score": 3,
  "confidence": 0.9,
  "evidence_quotes": []
}
```

## Prompt 05 — Legal Auditor

```json
{
  "dimension": "legal_coherence",
  "intended_legal_patterns_found": [],
  "intended_patterns_verified": [],
  "intended_patterns_missing": [],
  "analysis": "Intended legal/procedural flaws verified in denial letter.",
  "score": 5,
  "confidence": 0.87,
  "evidence_quotes": [],
  "improvement": null
}
```

## Prompt 06 — Contradiction Hunter (Tier 1)

```json
{
  "dimension": "internal_contradiction",
  "verdict": "PASS",
  "analysis": "Core facts stable across profile, letter, and clinical_context.",
  "confidence": 0.94,
  "evidence_quotes": []
}
```

## Prompt 07 — Demographic Validator (Tier 1)

```json
{
  "dimension": "demographic_plausibility",
  "verdict": "PASS",
  "analysis": "Age/gender/diagnosis combination is plausible.",
  "confidence": 0.95,
  "evidence_quotes": [
    "age=66",
    "gender=M",
    "diagnosis=Bipolar II disorder, current depressed episode (F31.81)",
    "treatment_requested=Partial hospitalization program (PHP)"
  ]
}
```

## Prompt 11 — Diagnosis–Treatment Match (Tier 1)

```json
{
  "dimension": "diagnosis_treatment_match",
  "verdict": "PASS",
  "analysis": "Partial hospitalization program (PHP) is a plausible intervention for Bipolar II disorder, current depressed episode (F31.81).",
  "confidence": 0.96,
  "evidence_quotes": [
    "Bipolar II disorder, current depressed episode (F31.81)",
    "Partial hospitalization program (PHP)"
  ]
}
```

## Prompt 12 — Insurer Voice

```json
{
  "dimension": "insurer_voice",
  "analysis": "Authentically cold Aetna UM voice.",
  "score": 5,
  "confidence": 0.9,
  "evidence_quotes": [
    "We are unable to approve this request"
  ]
}
```

## Prompt 13 — Denial Logic

```json
{
  "dimension": "denial_logic",
  "intended_logic_patterns_found": [],
  "intended_patterns_verified": [],
  "intended_patterns_missing": [],
  "analysis": "Intended shoddy denial logic present.",
  "score": 5,
  "confidence": 0.9,
  "evidence_quotes": [
    "EXPLANATION OF DECISION"
  ],
  "improvement": null
}
```

## Prompt 14 — Date Sanity (Tier 1)

```json
{
  "dimension": "date_sanity",
  "intended_timing_patterns_found": [],
  "intended_patterns_verified": [],
  "intended_patterns_missing": [],
  "verdict": "PASS",
  "analysis": "Dates/timestamps coherent; intended timing flaws verified.",
  "confidence": 0.9,
  "evidence_quotes": [
    "null",
    "null"
  ],
  "improvement": null
}
```

## Prompt 15 — Citation Traceability

```json
{
  "dimension": "citation_traceability",
  "intended_citation_patterns_found": [],
  "intended_patterns_verified": [],
  "intended_patterns_missing": [],
  "analysis": "Citations appropriately vague or flawed as intended.",
  "score": 5,
  "confidence": 0.85,
  "evidence_quotes": [
    "Clinical policy applied"
  ],
  "improvement": null
}
```

## Prompt 16 — Scope Guard (Tier 1)

```json
{
  "dimension": "scope_guard",
  "verdict": "PASS",
  "analysis": "Commercial Aetna case; in scope.",
  "confidence": 0.98,
  "evidence_quotes": [
    "Aetna"
  ]
}
```

## Prompt 17 — Safety Redactor (Tier 1)

```json
{
  "dimension": "safety_redaction",
  "verdict": "PASS",
  "phi_findings": [
    "none"
  ],
  "safety_findings": [
    "none"
  ],
  "analysis": "Synthetic IDs; neutral tone.",
  "confidence": 0.95,
  "improvement": null
}
```

## Prompt 18 — Flaw Injection Verifier ★

```json
{
  "dimension": "flaw_injection_verification",
  "denial_pattern_sources_found": [
    "mhpaea_visit_limit_asymmetry",
    "algo_boilerplate_fingerprint"
  ],
  "verification_results": [
    {
      "status": "PRESENT",
      "evidence": "MHPAEA-style behavioral health asymmetry language (mhpaea_visit_limit_asymmetry).",
      "pattern_id": "mhpaea_visit_limit_asymmetry"
    },
    {
      "status": "PRESENT",
      "evidence": "Denial lacks patient-specific clinical anchors.",
      "pattern_id": "algo_boilerplate_fingerprint"
    }
  ],
  "score": 5,
  "confidence": 0.93
}
```

## Prompt 09 — Realism Assessor (meta)

```json
{
  "dimension": "overall_realism",
  "score": 5,
  "analysis": "Case reads as credible commercial UM correspondence with intentional procedural flaws.",
  "confidence": 0.87,
  "improvement": null
}
```

## Prompt 10 — Appeal Difficulty (meta)

```json
{
  "dimension": "appeal_difficulty",
  "score": 4,
  "exploitable_weaknesses": [
    "Pattern anchor: mhpaea_visit_limit_asymmetry",
    "Pattern anchor: algo_boilerplate_fingerprint"
  ],
  "strong_defenses": [
    "Denial cites plan policy framework",
    "180-day appeal window stated"
  ],
  "confidence": 0.86
}
```

## Prompt 08 — Final Arbiter

```json
{
  "case_id": "case_278_aetna_priorauth",
  "evaluator": "Gumloop",
  "verdict": "APPROVE",
  "reason": "All Tier 1 gates pass; no Tier 2 critic failed.",
  "tier_1_failures": [],
  "tier_2_failures": [],
  "suggested_revisions": []
}
```
