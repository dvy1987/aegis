---
name: run-case-generate
description: >
  Manually runs the whole synthetic case generation pipeline faithfully, including 
  diversification, drafting, flaw injection, and invoking subagents for Gumloop-style 
  evaluation.
---

# /run-case-generate

You are executing `llm_pipeline.py::generate_one_case()` manually. Every step below maps
to a specific function call in that file. You MUST execute every step in order. You MUST
NOT skip, merge, or abbreviate any step. You MUST NOT invent shortcuts.

MAX_SCENARIO_RETRIES = 4. MAX_STAGE_REVISIONS = 2.

If any hard-gate fails after exhausting retries, discard and re-roll the entire case from
Step 0. Track which retry you are on. If you exhaust 4 retries, report failure — do not
silently produce a lower-quality case.

Write every intermediate output to a scratch file so it can be verified.

---

## Step 0: Pre-flight — Data Loading

**DO:**
1. Read `eval/diversity_matrix.json`. Extract all axes (insurer, denial_type, specialty,
   patient_age_band, patient_gender, sub_tactic_medical_necessity,
   sub_tactic_prior_authorization) and joint_constraints.
2. Read `eval/denial_patterns.json`. Load all 24 patterns.
3. Read `eval/clinical_variants.json`. Load all specialties and their variants.
4. Read `eval/denial_rationale_seeds.json`. Load all sub_tactic seeds.
5. Read `eval/banned_topics.json`. Load all banned topics and their deterministic_patterns.
6. Read `eval/case_schema.json`. Keep for Step 17.
7. Scan `eval/cases/drafts/` — list all existing case files. Build a set of
   `(insurer, denial_type, specialty, sub_tactic)` tuples already used (= `accepted_cells`).
   Also build a list of `neighbour_summaries` from existing cases:
   `"- [insurer / denial_type / specialty / sub_tactic] dx=...; tx=..."`.
8. Read `eval/references/denial-letter-realism-sources.json` and
   `eval/references/web-research-cache-2026-06-02.json`. Keep for Step 16.

**OUTPUT:** All data loaded into working memory. Write a summary to scratch file
`scratch/00_preflight.md` listing: how many existing cases, which cells are taken,
how many neighbour summaries.

---

## Step 1: Sample Matrix Cell + Denial Patterns

**DO (replicates `config.sample_matrix_cell` + `config.sample_denial_patterns`):**
1. Pick a matrix cell by weighted random from `diversity_matrix.json` axes. The cell must
   NOT be in `accepted_cells`. If it is, re-sample (up to 64 tries).
   Result: `cell = {insurer, denial_type, specialty, patient_age_band, patient_gender, sub_tactic}`.
   - `sub_tactic` comes from `sub_tactic_medical_necessity` or `sub_tactic_prior_authorization`
     depending on `denial_type`.
2. Sample 2 denial patterns from `denial_patterns.json` where:
   - `insurer` is in the pattern's `insurer_affinity`
   - If pattern category is `mhpaea_parity`, specialty must be `behavioral_health`
   - Try to pick from different categories.
   Result: `patterns = [{id, category, description, source, ...}, ...]`
3. Extract: `pattern_ids_list = [p.id for p in patterns]`

**OUTPUT:** Write `scratch/01_cell_and_patterns.json` with `{cell, patterns, pattern_ids_list}`.

---

## Step 2: P1 — Scenario Planner (YOU are the producer)

**READ:** `backend/app/case_generator/prompts/p1_scenario_planner.txt`

**DO (replicates `_scenario_planner_stage` → `agents.run_scenario_planner`):**
1. Gather P1 inputs:
   - `joint_constraints`: render `diversity_matrix.json` → `joint_constraints` array as
     bullet list.
   - `sub_tactic_definition`: find the matching sub_tactic entry in the matrix, use its
     `definition` field.
   - `specialty_examples`: find the matching specialty entry, use its `examples` array.
   - `clinical_variants`: from `clinical_variants.json`, get up to 12 variants for this
     specialty. Render as:
     ```
     - dx: {diagnosis} [sex: M/F if constrained]
       tx: {treatment_requested}
       facts: {clinical_facts}
     ```
   - `rationale_seed`: from `denial_rationale_seeds.json`, get the seed for this sub_tactic.
     Prepend: "Denial-rationale exemplar for this sub_tactic (adapt with the real dx/tx,
     do not copy verbatim): {denial_rationale}"
   - Append the rationale_seed to `sub_tactic_definition` if it exists.
   - `patterns_json`: the sampled patterns from Step 1.
2. Fill the P1 prompt template with these variables.
3. Roleplay the ScenarioPlanner agent faithfully. Produce the ScenarioBrief JSON:
   ```json
   {
     "matrix_cell": {same as cell},
     "diagnosis": "...",
     "treatment_requested": "...",
     "denial_rationale_seed": "...",
     "rebuttal_seed": "...",
     "patient_age": <integer>,
     "patient_gender": "M"|"F"|"nonbinary",
     "plan_funding_type": "fully_insured"|"self_funded",
     "employer_archetype": "<string if 71+ else null>",
     "intended_appeal_difficulty": <1, 3, or 5>,
     "intended_flaw_types": ["<flaw1>", "<flaw2>"],
     "intended_flaw_categories": ["<cat1>", "<cat2>"]
   }
   ```

**DETERMINISTIC SEX GUARD (replicates `clinical_kb.required_sex`):**
After producing the brief, check: does the diagnosis or treatment match a sex-specific
condition?
- Female-only regex: `ovarian|ovary|menorrhagia|adenomyosis|endometri|uterine|PCOS|cervix|
  cervical cancer|vagin|fibroid|macromastia|breast cancer|uterine prolapse|pregnan|
  gestational|fallopian|vulv|gynecolog`
- Male-only regex: `gynecomastia|prostat|testicular|testis|male hypogonadism|erectile|
  penile|scrotal|varicocele|BPH|benign prostatic`
- If diagnosis/treatment matches female regex → force `patient_gender = "F"`
- If matches male regex → force `patient_gender = "M"`
- Override the brief's gender if it conflicts.

**PLAN FUNDING GUARD:** If any sampled pattern has category `coverage_interpretation` that
requires state mandates (e.g., `plan_exclusion_overrides_state_mandate`), force
`plan_funding_type = "fully_insured"`.

**OUTPUT:** Write `scratch/02_scenario_brief.json`.

---

## Step 3: P1 Critics (SUBAGENTS — 2 in parallel)

**READ:** `backend/app/case_generator/prompts/c_matrix_coverage.txt` and
`backend/app/case_generator/prompts/c_scenario_realism.txt` and
`backend/app/case_generator/prompts/_critic_envelope.txt`.

**DO:** Spawn 2 `research` subagents in parallel:

**Subagent A — MatrixCoverageCritic (HARD GATE, PASS/FAIL):**
- Send the FULL text of `c_matrix_coverage.txt` with variables filled:
  - `{assigned_matrix_cell_json}` = the cell from Step 1
  - `{scenario_brief_json}` = the brief from Step 2
  - `{envelope}` = full text of `_critic_envelope.txt`
- DO NOT send: `intended_flaw_types`, `intended_appeal_difficulty`, patterns, or any
  generation context beyond what the prompt template requires.
- Expected output: JSON with `"score": "PASS"` or `"FAIL"`.

**Subagent B — ScenarioRealismCritic (WEIGHTED, 1/3/5):**
- Send the FULL text of `c_scenario_realism.txt` with variables filled:
  - `{scenario_brief_json}` = the brief from Step 2
  - `{envelope}` = full text of `_critic_envelope.txt`
- Expected output: JSON with `"score": 1, 3, or 5`.

**GATE:**
- If MatrixCoverage = FAIL → increment stage revision counter. If < 2 revisions, go back
  to Step 2 with the critic's `improvement` feedback. If ≥ 2 revisions → ScenarioDiscarded,
  go to Step 1 and re-sample (counts as 1 retry out of 4).
- If ScenarioRealism = 1 → same retry logic as above.
- If both pass → proceed.

**OUTPUT:** Write `scratch/03_p1_critics.json` with both verdicts.

---

## Step 4: P2 — Denial Drafter (YOU are the producer)

**READ:** `backend/app/case_generator/prompts/p2_denial_drafter.txt`

**DO (replicates `_denial_drafter_stage` → `agents.run_denial_drafter`):**
1. Fill the P2 prompt with `{scenario_brief_json}` = the brief from Step 2.
2. Roleplay the DenialLetterDrafter agent. Produce:
   ```json
   {"denial_letter_text": "Dear Member,...", "denial_pattern_sources": ["source1", "source2"]}
   ```
3. The letter MUST be 200–500 words.
4. The letter MUST match the insurer voice (Aetna/Cigna/UHC).
5. The letter MUST align with the sub_tactic from the brief.
6. If `intended_flaw_types` includes a `missing_*` flaw, you MUST OMIT the thing it says
   is missing. The omission IS the feature.

**OUTPUT:** Write `scratch/04_denial_letter.json`. Extract `letter = denial_letter_text`.

---

## Step 5: P2 Critics (SUBAGENTS — 2 in parallel)

**READ:** `backend/app/case_generator/prompts/c_insurer_voice.txt` and
`backend/app/case_generator/prompts/c_denial_logic.txt`.

**Subagent C — InsurerVoiceCritic (WEIGHTED, 1/3/5):**
- Variables: `{insurer}` = cell.insurer, `{denial_letter_text}` = letter from Step 4.
  `{envelope}` = envelope text.

**Subagent D — DenialLogicCritic (WEIGHTED, 1/3/5):**
- Variables: `{sub_tactic}` = cell.sub_tactic,
  `{sub_tactic_definition}` = definition from diversity_matrix,
  `{denial_letter_text}` = letter from Step 4. `{envelope}` = envelope text.

**GATE:** If either scores 1 and revisions < 2, go back to Step 4 and redraft. If ≥ 2
revisions, proceed with what you have (the pipeline does the same).

**OUTPUT:** Write `scratch/05_p2_critics.json`.

---

## Step 6: P3 — Clinical Writer (YOU are the producer)

**READ:** `backend/app/case_generator/prompts/p3_clinical_writer.txt`

**DO (replicates `_clinical_writer_stage` → `agents.run_clinical_writer`):**
1. Fill P3 prompt with:
   - `{scenario_brief_json}` = the brief
   - `{denial_letter_text}` = the letter from Step 4
2. Roleplay the ClinicalContextWriter. Produce:
   ```json
   {"clinical_context": "The 42-year-old member has..."}
   ```
3. Context MUST be 80–250 words.
4. Context MUST factually contradict the denial rationale.
5. Context MUST include specific clinical facts (drugs, doses, durations, scores, dates).

**OUTPUT:** Write `scratch/06_clinical_context.json`. Extract `ctx = clinical_context`.

---

## Step 7: P3 Critics (SUBAGENTS — 2 in parallel)

**READ:** `backend/app/case_generator/prompts/c_clinical_realism.txt` and
`backend/app/case_generator/prompts/c_diagnosis_treatment_match.txt`.

**Subagent E — ClinicalRealismCritic (WEIGHTED, 1/3/5):**
- Variables: `{diagnosis}`, `{treatment_requested}`, `{clinical_context}` = ctx.
  `{envelope}` = envelope text.

**Subagent F — DiagnosisTreatmentMatchCritic (HARD GATE, PASS/FAIL):**
- Variables: `{diagnosis}`, `{treatment_requested}`. `{envelope}` = envelope text.

**GATE:**
- DiagnosisTreatmentMatch FAIL → retry Step 6 (up to 2 revisions).
- ClinicalRealism = 1 → retry Step 6.

**OUTPUT:** Write `scratch/07_p3_critics.json`.

---

## Step 8: P4 — Realistic Flaw Injector (YOU are the producer)

**READ:** `backend/app/case_generator/prompts/p4_realistic_flaw_injector.txt`

**DO (replicates `_flaw_injector_stage` → `agents.run_realistic_flaw_injector`):**
1. Assemble the case so far:
   ```json
   {
     "matrix_cell": cell,
     "diagnosis": brief.diagnosis,
     "treatment_requested": brief.treatment_requested,
     "denial_letter_text": letter,
     "clinical_context": ctx
   }
   ```
2. Fill the P4 prompt with:
   - `{assembled_case_json}` = the assembled case
   - `{intended_flaw_types}` = from the brief
   - `{patterns_json}` = the sampled patterns
3. Roleplay the RealisticFlawInjector. Produce:
   ```json
   {
     "denial_letter_text": "...(with flaws injected)...",
     "clinical_context": "...",
     "diagnosis": "...",
     "treatment_requested": "...",
     "submission_timestamp": "<ISO8601 or null>",
     "denial_timestamp": "<ISO8601 or null>",
     "denial_pattern_sources": ["pattern_id: source", ...],
     "perturbation_notes": "..."
   }
   ```
4. CRITICAL: For each pattern in `patterns`, you MUST inject a concrete, discoverable
   trace into the letter/context. Consult `flaw_verifier.py`'s `_CHECKS` dict (read during
   pre-flight) to know EXACTLY what the deterministic verifier looks for. If the verifier
   will search for `"mcg"` in the letter for `step_therapy_vague_mcg`, make sure that string
   is present.
5. If `algo_time_delta` is a pattern: set `submission_timestamp` and `denial_timestamp`
   exactly 1–5 minutes apart AND include prose evidence of fast turnaround.

**OUTPUT:** Write `scratch/08_p4_output.json`. Build `assembled_for_p5 = {assembled ∪ p4_output}`.

---

## Step 9: Post-P4 Flaw Checkpoint (DETERMINISTIC — YOU do this)

**DO (replicates `_post_p4_flaw_checkpoint`):**
1. Run the deterministic flaw verifier checks from `flaw_verifier.py` against
   `assembled_for_p5`. For each `pattern_id` in `pattern_ids_list`, apply the matching
   `_chk_*` function logic:
   - Check the letter (lowercased) and context (lowercased) against the regex patterns
     defined in `flaw_verifier.py` (which you read in Pre-flight).
   - Classify each pattern as `present`, `absent`, or `needs_llm`.
2. If any pattern is `absent`:
   - Re-roleplay P4 (Step 8) for ONLY the absent patterns. Targeted re-injection.
   - Re-run the deterministic check.
3. This checkpoint is deterministic only — no subagent needed here. The full
   deterministic+LLM check runs after P5.

**OUTPUT:** Write `scratch/09_p4_checkpoint.json` with
`{present: [...], absent: [...], needs_llm: [...]}`.

---

## Step 10: P5 — Stylistic Diversifier (YOU are the producer)

**READ:** `backend/app/case_generator/prompts/p5_stylistic_diversifier.txt`

**DO (replicates `_stylistic_diversifier_stage` → `agents.run_stylistic_diversifier`):**
1. Fill the P5 prompt with:
   - `{assembled_case_json}` = `assembled_for_p5` from Step 8/9
   - `{neighbour_summaries}` = the neighbour summaries from Step 0, formatted as bullet list.
     If empty: "(this is the first case in the run)".
2. Roleplay the StylisticDiversifier. Produce:
   ```json
   {
     "denial_letter_text": "...",
     "clinical_context": "...",
     "diagnosis": "...",
     "treatment_requested": "...",
     "submission_timestamp": "<preserve exactly>",
     "denial_timestamp": "<preserve exactly>",
     "denial_pattern_sources": ["<preserve exactly>"],
     "stylistic_notes": "..."
   }
   ```
3. HARD RULES: DO NOT remove or mutate injected flaws. DO NOT change timestamps.
   DO NOT change denial_pattern_sources. Only diversify prose and clinical grounding.

**OUTPUT:** Write `scratch/10_p5_output.json`. This is now `stylized`.

---

## Step 11: P5 Critic + Text Metrics (SUBAGENT + DETERMINISTIC)

**Part A — Diversity Delta Critic (SUBAGENT):**

**READ:** `backend/app/case_generator/prompts/c_diversity_delta.txt`

**Subagent G — DiversityDeltaCritic (WEIGHTED, 1/3/5):**
- Build `this_case_summary`:
  `"- [insurer / denial_type / specialty / sub_tactic] dx=...; tx=..."`
- Variables: `{this_case_summary}`, `{neighbour_summaries}` = bullet list of neighbours
  (or "(no neighbours yet)"). `{envelope}` = envelope text.

**Part B — Text Metrics Guard (DETERMINISTIC — you do this):**
1. Count words in `stylized.denial_letter_text`. Must be 200–500.
   - If over 500: trim boilerplate (see `text_metrics.py::_LETTER_TRIMS` for the ordered
     trim list). Trim in order until under 500.
   - If under 200: add padding sentence about experimental/investigational definitions.
2. Count words in `stylized.clinical_context`. Must be 80–250.
   - If under 80: add a sentence about expedited reconsideration.
3. Check for P2P splice artifacts (a peer-to-peer sentence jammed into the middle of the
   provider-discussion sentence). Repair if found.

**Part C — Format denial_pattern_sources (DETERMINISTIC):**
Overwrite `stylized.denial_pattern_sources` with formatted strings:
`"{pattern_id}: {pattern_source}"` for each pattern. This is the format the teacher
packet parses.

**OUTPUT:** Write `scratch/11_text_metrics.json` with word counts and any trims applied.

---

## Step 12: Post-P5 Flaw Verification (DETERMINISTIC + SUBAGENT)

**DO (replicates `_flaw_injection_stage`):**

**Part A — Deterministic verification (YOU):**
Run the same `_chk_*` logic from Step 9 on the CURRENT `stylized` output.
Result: `{present, absent, needs_llm}`.

**Part B — LLM verification (SUBAGENT):**

**READ:** `backend/app/case_generator/prompts/c_flaw_injection_verifier.txt`

**Subagent H — FlawInjectionVerifier (HARD GATE):**
- Variables:
  - `{denial_letter_text}` = stylized letter
  - `{clinical_context}` = stylized context
  - `{submission_timestamp}` = stylized timestamp or "null"
  - `{denial_timestamp}` = stylized timestamp or "null"
  - `{patterns_to_check}` = for EACH pattern in `needs_llm` list (from Part A):
    `[{"id": "...", "description": "...", "appeal_vector": "..."}]`
- DO NOT send: intended_flaw_types, intended_appeal_difficulty, the brief, or generation
  context.
- Expected output: `{verification_results: [{pattern_id, status, evidence}], absent: [...]}`

**Part C — Union absent sets:**
`absent = set(deterministic_absent) ∪ set(llm_absent)`

**Part D — If absent is non-empty:**
1. Re-roleplay P4 (targeted re-injection for the absent patterns only).
2. Apply text metrics guard again.
3. Re-run Part A + Part B.

**GATE:** Final result must have `absent = []`. If still absent after re-injection, this
counts as a hard-gate fail → re-roll from Step 1 (counts against retry budget).

**OUTPUT:** Write `scratch/12_flaw_verification.json` with full results.

---

## Step 13: Statistical Diversity Check (DETERMINISTIC)

**DO (replicates `stats_evaluator.diversity_metrics` + `diversity_verdict`):**
1. Tokenize `stylized.denial_letter_text + "\n" + stylized.clinical_context` into
   lowercase alphanumeric tokens. Build trigram set.
2. For each existing case in `eval/cases/drafts/`, load its letter+context, build trigram
   set, compute Jaccard similarity.
3. Find the maximum Jaccard across all existing cases.
4. Thresholds:
   - `worst >= 0.50` → score 1 (near-duplicate, FAIL → re-roll)
   - `worst >= 0.35` → score 3 (acceptable but close)
   - `worst < 0.35` → score 5 (good diversity)
5. Score 1 → hard fail, re-roll from Step 1.

**OUTPUT:** Write `scratch/13_diversity_stats.json`.

---

## Step 14: Safety + PHI Gates (DETERMINISTIC + SUBAGENT)

**Part A — Deterministic banned-topic scan (YOU):**
For each topic in `banned_topics.json`, for each `deterministic_patterns` regex, search
`stylized.denial_letter_text + "\n" + stylized.clinical_context`.
If any match → HARD FAIL → re-roll from Step 1.

**Part B — Deterministic PHI scan (YOU):**
Search for: SSN (`\d{3}-\d{2}-\d{4}`), MRN (`MRN\s*#?:?\s*\w+`),
DOB (`DOB\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}`).
If any match → HARD FAIL → re-roll from Step 1.

**Part C — LLM Safety Critic (SUBAGENT, only if Part A passes):**

**READ:** `backend/app/case_generator/prompts/c_safety_redactor.txt`

**Subagent I — SafetyRedactorCritic (HARD GATE, PASS/FAIL):**
- Variables: `{banned_topic_briefs}` = rendered from banned_topics.json
  (`"- topic_id: label — llm_check_guidance"` per topic),
  `{denial_letter_text}`, `{clinical_context}`. `{envelope}` = envelope text.
- FAIL → re-roll from Step 1.

**OUTPUT:** Write `scratch/14_safety.json`.

---

## Step 15: Build patient_profile (DETERMINISTIC)

**DO:**
```json
{
  "age": brief.patient_age,
  "gender": brief.patient_gender,
  "diagnosis": stylized.diagnosis,
  "treatment_requested": stylized.treatment_requested,
  "plan_funding_type": brief.plan_funding_type (default "self_funded")
}
```

**OUTPUT:** Write `scratch/15_patient_profile.json`.

---

## Step 16: Final Panel — 10 Critics (SUBAGENTS, all in parallel)

**READ:** All 10 critic prompt files from `backend/app/case_generator/prompts/`.

Spawn 10 `research` subagents. NONE of them receive the brief, intended_flaw_types,
intended_appeal_difficulty, or any generation context. They receive ONLY their prompt
template variables.

| # | Subagent | Prompt file | Gate type | Key variables |
|---|---|---|---|---|
| J | ContradictionHunter | `c_contradiction_hunter.txt` | HARD (PASS/FAIL) | patient_profile_json, diagnosis, treatment_requested, denial_letter_text, clinical_context |
| K | LLMTellDetector | `c_llm_tell_detector.txt` | HARD (PASS/FAIL) | denial_letter_text, clinical_context, envelope |
| L | OverallTone | `c_overall_tone.txt` | WEIGHTED (1/3/5) | denial_letter_text, clinical_context, envelope |
| M | FinancialAuditor | `c_financial_auditor.txt` | WEIGHTED (1/3/5) | denial_letter_text, clinical_context, envelope |
| N | LegalAuditor | `c_legal_auditor.txt` | WEIGHTED (1/3/5) | denial_letter_text, clinical_context, envelope |
| O | DemographicValidator | `c_demographic_validator.txt` | WEIGHTED (1/3/5) | patient_profile_json, denial_letter_text, clinical_context, envelope |
| P | ScopeGuard | `c_scope_guard.txt` | HARD (PASS/FAIL) | patient_profile_json, insurer, denial_type, denial_letter_text, clinical_context, envelope |
| Q | DateSanity | `c_date_sanity.txt` | WEIGHTED (1/3/5) | denial_letter_text, clinical_context, envelope |
| R | CitationTraceability | `c_citation_traceability.txt` | WEIGHTED (1/3/5) | denial_letter_text, envelope |
| S | AppealDifficulty | `c_appeal_difficulty.txt` | INFO ONLY (never gates) | denial_letter_text, clinical_context, envelope |

**OUTPUT:** Write `scratch/16_final_panel.json` with all 10 verdicts.

---

## Step 17: Verdicts Summary (DETERMINISTIC)

**DO (replicates `_verdicts_summary`):**
1. Collect ALL critic verdicts from Steps 3, 5, 7, 11, 12, 14, 16.
2. The complete critic map is:
   - `matrix_coverage` (Step 3) — hard gate
   - `scenario_realism` (Step 3) — weighted
   - `insurer_voice` (Step 5) — weighted
   - `denial_logic` (Step 5) — weighted
   - `clinical_realism` (Step 7) — weighted
   - `diagnosis_treatment_match` (Step 7) — hard gate
   - `diversity_delta` (Step 11) — weighted
   - `flaw_injection_p4` (Step 9) — informational
   - `flaw_injection` (Step 12) — hard gate
   - `diversity_statistical` (Step 13) — weighted
   - `safety_redactor` (Step 14) — hard gate
   - `phi_pii` (Step 14) — hard gate
   - `contradiction_hunter` (Step 16) — hard gate
   - `llm_tell_detector` (Step 16) — hard gate
   - `overall_tone` (Step 16) — weighted
   - `financial_auditor` (Step 16) — weighted
   - `legal_auditor` (Step 16) — weighted
   - `demographic_validator` (Step 16) — weighted
   - `scope_guard` (Step 16) — hard gate
   - `date_sanity` (Step 16) — weighted
   - `citation_traceability` (Step 16) — weighted
   - `appeal_difficulty` (Step 16) — INFO ONLY, skip in verdict
3. HARD GATE DIMS: `matrix_coverage`, `diagnosis_treatment_match`, `safety_redactor`,
   `contradiction_hunter`, `llm_tell_detector`, `scope_guard`, `flaw_injection`.
   Any FAIL → entire case fails → re-roll from Step 1.
4. WEIGHTED DIMS: Any score of 1 → entire case fails → re-roll from Step 1.
5. `appeal_difficulty` is NEVER a gate — informational only.

**GATE:** If any failure → re-roll (counts as 1 retry). If pass → proceed.

**OUTPUT:** Write `scratch/17_verdicts.json` with `{ok: true/false, failures: [...]}`.

---

## Step 18: Case Assembly (DETERMINISTIC)

**DO (replicates case_obj construction in `generate_one_case` lines 624–667):**
1. Build `case_id`:
   - `short = "mednec"` if Medical Necessity, else `"priorauth"`
   - Determine the next available index by scanning existing case files.
   - `case_id = f"case_{index:02d}_{insurer.lower()}_{short}"`
2. Build `denial_letter_references` (replicates `references.select_letter_references`):
   - From `denial-letter-realism-sources.json`, pick refs by `insurer_affinity` and
     `denial_type_affinity`.
   - Always include `cms-abd-model-2011` and `erisa-29-cfr-2560-503-1`.
   - If `missing_iro_notice` in patterns → include `aca-2719-29-cfr-147-136`.
   - If `step_therapy_vague_mcg` → include `kff-2023-consumer-survey`.
   - If `circular_medical_necessity` → include `propublica-uncovered-2023`.
   - From `web-research-cache-2026-06-02.json`, get web refs for the insurer×denial_type
     pool. Merge with catalog refs, max 8 total, web refs first.
3. Build `provenance`:
   ```json
   {
     "generator_model": "manual-agent-pipeline",
     "run_id": "gen-{YYYYMMDD}-{HHMMSS}-{5hex}",
     "generated_at": "<ISO8601 now>",
     "matrix_cell": cell,
     "prompt_versions": <from prompts/__init__.py PROMPT_VERSIONS>,
     "banned_topic_filter_version": <from banned_topics.json .version>,
     "schema_version": <from case_schema.json .x-aegis-schema-version>,
     "diversity_matrix_version": <from diversity_matrix.json .version>,
     "critic_verdicts": <all critics from Step 17>,
     "human_summary": "Synthetic case for {insurer} {denial_type} / {specialty} / sub_tactic={sub_tactic}. Generated by manual agent pipeline with per-stage AlphaEval critics.",
     "appeal_difficulty": {
       "score": <from appeal_difficulty critic>,
       "reasoning": "...",
       "exploitable_weaknesses": [..., "Pattern anchor: {pid}" for each pattern],
       "strong_defenses": [...]
     }
   }
   ```
4. Build `case_obj`:
   ```json
   {
     "case_id": "...",
     "insurer": "...",
     "denial_type": "...",
     "patient_profile": <from Step 15>,
     "denial_pattern_sources": <formatted from Step 11C>,
     "denial_letter_references": <from this step>,
     "denial_letter_text": <stylized>,
     "clinical_context": <stylized>,
     "submission_timestamp": <stylized or null>,
     "denial_timestamp": <stylized or null>,
     "synthetic_provenance": <provenance>
   }
   ```

**OUTPUT:** Write `scratch/18_case_assembled.json`.

---

## Step 19: Schema Validation (DETERMINISTIC)

**DO (replicates `validator.validate_case`):**
1. Validate `case_obj` against `eval/case_schema.json` (JSON Schema Draft 2020-12).
2. Check every required field, type, enum, minLength, maxLength, pattern, minimum, maximum.
3. Key checks:
   - `case_id` matches pattern `^case_[0-9]{2,4}_(aetna|cigna|uhc)_(mednec|priorauth)$`
   - `insurer` ∈ ["Aetna", "Cigna", "UHC"]
   - `denial_type` ∈ ["Medical Necessity", "Prior Authorization"]
   - `patient_profile.age` 18–89, `gender` ∈ ["M","F","nonbinary"]
   - `denial_letter_text` length 1000–4500 characters
   - `clinical_context` length 400–1600 characters
   - `denial_pattern_sources` minItems 1, each item minLength 8
   - All provenance fields present and valid

**GATE:** If validation fails → re-roll from Step 1.

**OUTPUT:** Write `scratch/19_validation.json` with `{ok: true, errors: []}`.

---

## Step 20: Final Flaw Integrity Check (DETERMINISTIC + SUBAGENT)

**DO (replicates `_verify_flaws_full` with `llm_all=True` — the FINAL gate):**

This is the last-chance guarantee. After schema validation, after all critics pass, we
verify ONE MORE TIME that every single intended flaw is discoverable.

**Part A — Deterministic (YOU):**
Run `_chk_*` logic on the FINAL `case_obj.denial_letter_text` and `case_obj.clinical_context`.

**Part B — LLM (SUBAGENT) — ALL patterns, not just needs_llm:**

**Subagent T — FinalFlawIntegrityVerifier:**
- Same prompt as Step 12 Subagent H (`c_flaw_injection_verifier.txt`).
- But `{patterns_to_check}` = ALL patterns (not just `needs_llm` ones). This is the
  `llm_all=True` flag — the LLM independently re-checks EVERY intended flaw.
- Variables: `{denial_letter_text}`, `{clinical_context}`, `{submission_timestamp}`,
  `{denial_timestamp}`, `{patterns_to_check}` = all patterns with id/description/appeal_vector.

**Part C — Union: `final_absent = set(det_absent) ∪ set(llm_absent)`**

**Part D — Record in provenance:**
```json
"final_flaw_integrity": {
  "method": "deterministic+llm(all)",
  "expected_flaws": pattern_ids_list,
  "deterministic_present": [...],
  "llm_absent": [...],
  "absent": final_absent,
  "aligned": true/false
}
```

**GATE:** If `final_absent` is non-empty → HARD FAIL → re-roll from Step 1 (the flaw is
missing from the finished case; judges would penalise the learner for something they
cannot find).

**OUTPUT:** Write `scratch/20_final_flaw_integrity.json`.

---

## Step 21: Write to Disk

**DO:**
1. Write the final `case_obj` (with `final_flaw_integrity` added to provenance) to:
   `eval/cases/drafts/case_{NN}_{insurer}_{type}.json`
2. Update `accepted_cells` set.
3. Add this case's summary to `neighbour_summaries`.
4. Report success: case_id, insurer, denial_type, specialty, sub_tactic, patterns used,
   appeal_difficulty score, word counts, and all critic scores.

---

## HARD RULES — VIOLATIONS ARE UNACCEPTABLE

1. **No step skipping.** Every numbered step must execute. If you are tempted to merge
   steps, DON'T.
2. **No phantom critics.** Every critic must actually run as a subagent. You must wait for
   its response and record the verdict. You cannot "assume PASS".
3. **No answer-key leaking.** Subagents must NEVER see `intended_flaw_types`,
   `intended_appeal_difficulty`, or the scenario brief (except P1 critics which need it).
4. **No silent downgrades.** If a gate fails, you must re-roll or retry — not proceed anyway.
5. **No invented patterns.** Flaws come only from `eval/denial_patterns.json`.
6. **No PHI.** No SSN, MRN, DOB, real names.
7. **No banned topics.** Checked deterministically at Step 14.
8. **Write every intermediate output.** Every scratch file must exist before proceeding to
   the next step. This is your audit trail.
