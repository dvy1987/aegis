# Aegis Dataset Card (eval/cases/)

**Description:** This dataset contains the synthetic calibration and benchmark cases used to evaluate the Aegis multi-agent system. 

## Strict PHI Policy
As mandated by `AGENTS.md`, **NO REAL PROTECTED HEALTH INFORMATION (PHI)** is present in this dataset. Every case is 100% synthetically generated. 

## Provenance
- `case_01_cigna_mednec.json`: Cigna - Medical Necessity (OCD Intensive Outpatient Program).
- `case_02_cigna_priorauth.json`: Cigna - Prior Authorization (Cervical Spine MRI in ER).
- `case_03_aetna_mednec.json`: Aetna - Medical Necessity (Inpatient Detox for Alcohol Use).
- `case_04_aetna_priorauth.json`: Aetna - Prior Authorization (Humira continuation without new auth).
- `case_05_uhc_mednec.json`: UHC - Medical Necessity (CGM for Type 2 Diabetes without intensive insulin).
- `case_06_uhc_priorauth.json`: UHC - Prior Authorization (Out-of-network gap exception for endometriosis excision).
- `case_07_cigna_mednec.json`: Cigna - Medical Necessity (Bariatric Surgery, missing 6-month diet rule).
- `case_08_cigna_priorauth.json`: Cigna - Prior Authorization (Physical Therapy beyond 20 visits).
- `case_09_aetna_mednec.json`: Aetna - Medical Necessity (Breast reduction, missing conservative therapy).
- `case_10_uhc_priorauth.json`: UHC - Prior Authorization (In-lab sleep study over HSAT).

## Lifecycle & Splits
This dataset follows a strict lifecycle where cases begin as Drafts and must pass the Gumloop/Frontier Model evaluator swarm before being moved to Approved.

**Current Locations:**
- **Drafts - Part-A Train (`eval/cases/drafts/part-a/train/`):** 10 synthetic calibration cases drafted for MVP prompt tuning (`case_NN_<insurer>_<denial>.json`).
- **Drafts - Part-A Test (`eval/cases/drafts/part-a/test/`):** 10 first-generation held-out cases (`test_case_NN_…json`) plus newer generator-swarm-emitted cases (`case_NN_<insurer>_<denial>.json`).

*Note: Once evaluated, cases will be moved to `eval/cases/approved/...`*

## Generation Pipeline

Cases prefixed `case_NN_<insurer>_<denial>.json` (new naming) are produced by the AlphaEval-aligned generator swarm at `backend/app/case_generator/`:

```
ScenarioPlanner → DenialDrafter → ClinicalContextWriter → AdversarialDiversifier
  → SafetyRedactor (deterministic + LLM) → SchemaValidator
  → FinalAssemblyMiniPanel (Contradiction · LLM-Tell · Tone · Financial · Legal · Demographic · Scope · DateSanity · CitationTraceability)
```

Per-stage **independent** critics enforce AlphaEval rules: forced 1/3/5 anchors on weighted dimensions, binary PASS/FAIL hard gates that short-circuit, CoT-before-score, no mega-prompts. Every critic verdict is captured in `synthetic_provenance.critic_verdicts` for auditability.

The Gumloop swarm in `gumloop/` is an **independent second-opinion evaluator** — cases move from `drafts/` to `approved/` only on Gumloop `APPROVE`.

Configs:
- Diversity matrix (weighted sampling): `eval/diversity_matrix.json`
- Banned-topic hard-gate list: `eval/banned_topics.json`
- JSON Schema: `eval/case_schema.json`

Run: `cd backend && uv run python -m app.case_generator.cli --count <N> --split {train|test}`.
