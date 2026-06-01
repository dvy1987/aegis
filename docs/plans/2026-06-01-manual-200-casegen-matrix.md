# Manual 200-case generation (cases 11–210)

| Setting | Value |
|---------|--------|
| Method | Cursor manual swarm (`manual_producer.py`) — **no Vertex Gemini** |
| Output dir | `eval/cases/drafts/benchmark-200/` |
| Batch size | 10 cases |
| Batches | 20 (batch 1 = cases 11–20 … batch 20 = 201–210) |
| CLI | `cd backend && uv run python scripts/run_manual_case_batch.py --batch N` |

## Swarm agents executed per case

**Producers:** P1 ScenarioPlanner → P2 DenialDrafter → P3 ClinicalWriter → P4 RealisticFlawInjector → P5 StylisticDiversifier

**Stage critics:** matrix_coverage, scenario_realism, insurer_voice, denial_logic, clinical_realism, diagnosis_treatment_match

**Final panel:** contradiction_hunter, llm_tell_detector, overall_tone, financial_auditor, legal_auditor, demographic_validator, scope_guard, date_sanity, citation_traceability, appeal_difficulty

**Deterministic gates:** safety_redactor, phi_pii

## After each batch

1. Validate: `cd backend && uv run python scripts/validate_manual_batch.py --batch N`
2. Append handoff to `docs/memory/agent-handoffs.md`
3. Git commit
