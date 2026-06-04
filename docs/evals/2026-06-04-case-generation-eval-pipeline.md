# Eval Pipeline: Aegis Case Generator (LLM swarm)

System: `backend/app/case_generator/llm_pipeline.py` (Gemini producer→critic swarm).
Maturity stage: 4. Critical outputs: synthetic denial cases (letter + clinical context +
metadata) used to train/benchmark the Aegis appeal agent and judges.

Aligns the **generation** pipeline to AlphaEval 2026 + the `eval-pipeline` skill: three
evaluator types, forced 1/3/5 anchors, binary hard gates that short-circuit, independent
single-dimension judges (no mega-prompt), per-step checkpoints (cascade-dependency), and
test-your-tests (known-bad fixtures).

## Evaluator Stack

### Layer 1 — Deterministic (fast, no LLM)
- **Sex guard** (`clinical_kb.required_sex`) — forces patient_gender to a sex-specific dx.
- **Flaw verifier** (`flaw_verifier.verify_flaws`) — every `denial_pattern_source` discoverable in student-visible prose (J6 contract); `format_pattern_sources` → teacher-packet-parseable `{id}: {source}`.
- **text_metrics** — 200–500-word letter / 80–250 clinical budget + artifact repair.
- **Safety/PHI** (`safety.scan_banned` / `scan_phi`) — regex hard gates.
- **Schema** (`validator.validate_case`).

### Layer 2 — Statistical (numeric, trend-trackable, no LLM)
- **`stats_evaluator.diversity_metrics`** — trigram-Jaccard near-duplicate vs the WHOLE existing drafts corpus + neighbours. Verdict 5 (<0.35) / 3 (<0.50) / 1 (≥0.50 → re-roll). This is the "diversify vs existing cases" mechanism. (Existing aplus drafts measure ~0.56 to each other — the templating problem, now quantified.)

### Layer 3 — LLM-as-judge (forced 1/3/5 or PASS/FAIL, independent per dimension)
P1: matrix_coverage*, scenario_realism · P2: insurer_voice, denial_logic · P3: clinical_realism, diagnosis_treatment_match* · P5: diversity_delta · flaw_injection_verifier (semantic) · Final panel: contradiction_hunter*, llm_tell_detector*, scope_guard*, safety_redactor*, demographic_validator, date_sanity, citation_traceability, overall_tone, financial_auditor, legal_auditor, appeal_difficulty. (* = binary hard gate.)
Judge model: `AEGIS_CASEGEN_CRITIC_MODEL` (ideally non-Gemini to avoid self-enhancement bias). Temp 0.2.

## Checkpoints (per-step, AlphaEval cascade-dependency)
- **P1** → matrix_coverage/scenario_realism + ≤2 stage-local revisions; FAIL → re-roll.
- **P2** → insurer_voice/denial_logic + ≤2 revisions.
- **P3** → clinical_realism/dx_tx + ≤2 revisions.
- **P4 → checkpoint BEFORE P5** (`_post_p4_flaw_checkpoint`): deterministic flaw verify + re-inject absent flaws so P5 never diversifies a flaw-broken letter.
- **P5** → diversity_delta + statistical near-dup.
- **Assembly** → safety/PHI, flaw_injection (det+LLM) hard gate, full critic panel, schema.
- **FINAL flaw-integrity gate (last step)** → `_verify_flaws_full(..., llm_all=True)` on the FINISHED `case_obj`: deterministic + LLM re-checks **every** intended flaw (the same patterns fed to the judges via `denial_pattern_sources` + `appeal_difficulty.exploitable_weaknesses`). `llm_all=True` means the LLM re-confirms even flaws the deterministic layer marked present, catching deterministic false-positives. Any absent → re-roll. Stamped to `synthetic_provenance.final_flaw_integrity`. This is the hard guarantee that judges never penalise the learner for a flaw the data fails to contain.

Hard gates short-circuit (`HARD_GATE_DIMS`): matrix_coverage, diagnosis_treatment_match, safety_redactor, contradiction_hunter, llm_tell_detector, scope_guard, flaw_injection.

## Dataset / known-bad
- Known-bad fixtures: `backend/tests/unit/case_generator/test_generation_gates.py` — 10 tests proving each deterministic evaluator catches its failure (absent flaw, sex mismatch, near-duplicate, PHI/SSN, banned topic, too-short schema) and passes its good case.

## Versioning
`prompt_versions` (incl. `c_flaw_injection_verifier`), `schema_version`, `diversity_matrix_version`, `banned_topic_filter_version` stamped into every case's provenance.

## Known gaps / follow-ups
- LLM-judge critics are exercised only via the live Gemini path (no creds in CI here) — add a sampled nightly run once creds are available.
- `diversity_statistical` DUP_FAIL=0.50 is tunable; re-baseline once the LLM pipeline (not aplus templates) produces the corpus.
