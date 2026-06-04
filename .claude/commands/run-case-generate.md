---
description: Faithfully run the full LLM case-generation pipeline end-to-end (you = producers P1–P5, evaluators = isolated subagents) and write real cases to eval/cases/drafts/.
---

# /run-case-generate

Generate synthetic denial case(s) by executing the **real** pipeline
(`backend/app/case_generator/llm_pipeline.py`) end-to-end — never a reimplementation. There
is no Gemini in this environment, so generation is split to stay faithful to AlphaEval:

- **YOU** (orchestrator) play the **PRODUCERS** (P1–P5) — the generator.
- **Every EVALUATOR runs as an ISOLATED SUBAGENT** that sees ONLY the artifact + rubric,
  never the generator's intent (independent-judge rule — no self-enhancement / contamination).
- The `manual_driver` feeds producers + subagent verdicts into the real `generate_one_case`,
  so every deterministic step runs for real: sex guard, per-stage gates + revisions, post-P4
  checkpoint, P5, text_metrics, **statistical near-dup vs the existing corpus (diversify)**,
  safety/PHI, full critic panel, schema, and the **final det+LLM flaw-integrity gate**.

Args (all optional): `--index N` (default: next free slot in drafts), `--seed S`
(default: choose one), `--count K` (default 1). Base dir for all commands: `backend`, run as
`PYTHONPATH=. .venv/bin/python -m app.case_generator.manual_driver <subcmd>`.

## Per case — do EXACTLY these steps in order. Skip nothing. Fake nothing.

### 1 — Prep
`manual_driver prep --index <N> --seed <S>`
Read the printed matrix cell, intended flaws (+appeal vectors), sub-tactic definition + seed,
clinical-KB grounding, and the EXISTING cases in this specialty.

### 2 — Author the producers (you are the generator)
Follow the real prompt files faithfully (read them):
`prompts/p1_scenario_planner.txt` → brief. Choose a dx/tx from the KB grounding (respect each
`[sex]` tag and the SEX-CONSISTENCY hard rule) that is **clearly different from the existing
specialty cases** (diversify). `p2_denial_drafter.txt` → denial letter that makes **every**
intended flaw discoverable in the prose (use the appeal-vectors), honoring the "do NOT negate
a `missing_*` flaw" rule (200–500 words). `p3_clinical_writer.txt` → clinical_context (80–250
words; specific facts that contradict the denial). `p4_realistic_flaw_injector.txt` → ensure
all flaws are embedded; set `submission_timestamp`/`denial_timestamp` if `algo_time_delta` or
`timeline_violation` is intended. `p5_stylistic_diversifier.txt` → diversify prose vs
neighbours, PRESERVE every flaw.
Write `/tmp/manual_run/producers.json` with keys `run_scenario_planner`, `run_denial_drafter`,
`run_clinical_writer`, `run_realistic_flaw_injector`, `run_stylistic_diversifier`. The last two
carry the FINAL letter/clinical + timestamps + denial_pattern_sources.

### 3 — Build isolated evaluator prompts
`manual_driver bundles --producers /tmp/manual_run/producers.json`
→ writes 19 self-contained critic prompts to `/tmp/manual_run/critics/`.

### 4 — Dispatch one ISOLATED subagent per evaluator
For each `/tmp/manual_run/critics/*.txt`, dispatch a `general-purpose` subagent whose entire
prompt is: *"Read the file `<abs path>`. It is a self-contained evaluation prompt. Follow it
exactly and return ONLY the JSON object it specifies — nothing else."* Run them in parallel
(multiple Agent calls in one message). **Do not** tell any subagent the intended flaws, the
matrix intent, or how the case was produced — isolation is the point.
Collect their JSON into:
- `/tmp/manual_run/critics.json` → `{dim: verdict}` for the 18 critic dims (filename minus `.txt` = dim).
- `/tmp/manual_run/flaws.json` → `{pattern_id: PRESENT|ABSENT}` built from `flaw_injection_verifier.txt`'s `verification_results`.

### 5 — Run the real pipeline
`manual_driver run --index <N> --seed <S> --producers /tmp/manual_run/producers.json --critics /tmp/manual_run/critics.json --flaws /tmp/manual_run/flaws.json`
- Success → writes `eval/cases/drafts/case_<N>_<insurer>_<type>.json`; prints `final_flaw_integrity` + `diversity_statistical`.
- Failure → the driver prints which gate failed (a critic scored 1/FAIL, a flaw judged ABSENT, or near-duplicate). **Fix `producers.json`** (re-draft to add the missing flaw / increase diversity), re-run `bundles`, **re-judge only the affected evaluator(s)** with fresh subagents, then re-run step 5. Never hand-edit a verdict to force a pass.

### 6 — Report
Tell the user: the `case_id` written, `final_flaw_integrity` (aligned + which flaws survived),
and the diversity score. For `--count K > 1`, repeat from step 1 with `index+1` and a new seed.

## Faithfulness rules (never violate)
- Evaluators are ALWAYS isolated subagents — never judge your own producer output in the main context.
- Never skip a step or fabricate a verdict. A failed gate = fix the case and re-judge, not override.
- Every intended flaw (the same set passed to the judges via `denial_pattern_sources` +
  `appeal_difficulty.exploitable_weaknesses`) must survive to the finished case — the pipeline's
  final det+LLM gate enforces this; if it re-rolls, fix the producers (the stub can't serve a new cell).
