# Question Agent — Test & Verification Handoff

Date: 2026-06-10 (updated post-verification)
Status: **shipped and verified** — backend Phases 1–7, `/appeal` chat step, US geo playbook wiring, question-agent prompt promotion activation, and approval-modal preview for question-agent diffs. Backend unit suite: **446 passed** (`uv run pytest tests/unit` from `backend/`). Frontend vitest: **28 passed**. Frontend `tsc` still has 8 pre-existing errors in `statusPreviewBatch.test.ts` only.

Design doc: `docs/specs/2026-06-10-question-agent-design.md`
Geo playbook plan (implemented): `docs/plans/2026-06-10-geo-playbook-plan.md`
Key invariants: appeal Q&A = traced, NOT graded; showcase Q&A = graded; INV-QA = student/question agent never sees teacher `clinical_context` in showcase.

## ROUND 2 redesign (read this first — supersedes parts of the file list below)
1. **Question agent is now a node INSIDE the ADK student workflow** (`student_workflow.question_agent_node`, between `library_finalize_node` and `drafter_prep_node`), not an orchestration-layer wrapper. Injection seams: `_injected_question_responder` / `_injected_question_client` module globals, set by `pipeline.run_aegis_v1_adk_pipeline` (new params `run_question_agent`, `question_responder`, `question_agent_client`, `question_interview`). On showcase the teacher clinical file lives ONLY in the responder closure (INV-QA); on appeal the finished HTTP interview is injected via `question_interview_json` state. The artifact is surfaced on `AppealPackage.question_interview` (new optional schema field).
2. **Insurer-wide playbook bundle**: `tools.insurer_playbook_bundle(insurer)` loads EVERY playbook for the insurer — the question agent never receives a denial-type-filtered playbook (denial type is not knowable a priori). The drafter's own playbook loading is unchanged.
3. **Prep sources**: the node reads Phoenix summary + library retrieval from workflow state; the appeal session store (`question_session.start`) does its own best-effort prep (bundle + `phoenix_mcp_lookup(insurer, "unknown")` + `corpus_retrieval`). `decide()` gained a `library_context` kwarg (protocol change — all client impls updated).
4. **Question judge is an LLM agent**: `GeminiQuestionJudgeClient` (structured output) used on the live/ADK panel path; the deterministic judge is the offline path AND the failure fallback. Part B is now teacher-driven: it mines regulatory/legal/insurer facts embedded in the hidden synthetic clinical file into targeted append-first instructions ("Add to playbook:<insurer:denial_type:sub_tactic>: ..." or "Add to global playbook: ...") that ride panel metadata + laundered improvement notes into Phoenix → GEPA reflection. The old "Collect from patient" recs are gone.
5. **Switched ON**: showcase `_measure` (with teacher context from `case.judge_case()`), `_seed_training_signal`, and `_eval_post_gepa_candidate` all pass `run_question_agent=True`. The appeal chat step is always on in the UI. Library/eval function defaults remain `False` so existing tests are unaffected unless a call site opts in.
6. **Appeal API**: `QuestionStartRequest` lost `denial_type` (insurer only); `create_appeal` threads the full interview artifact into the orchestrator/pipeline so it rides the trace.
7. **US geo playbook (no longer deferred)**: `geo_playbooks/us_playbook.json` + `backend/app/aegis_v1/geo_playbook.py` load insurer-agnostic rules into the student workflow (`geo_playbook_loader_node`), drafter message, and question-agent prep (`question_agent_prep_bundle`). GEPA seeds/mutates `geo_playbook:us` in the coordinator; promotion writes `us_playbook.json` via `fs_store._write_us_playbook`; showcase passes `geo_playbook_override` on measure/eval; approval modal shows US-playbook rule diffs via `promotion_preview.py`. Question-judge “Add to global playbook” recs route into US-playbook reflection; slice recs stay on slice playbooks.
8. **Post-verification fixes**: promoted `question_agent_system_prompt` now activates like the drafter (`active_question_agent_prompt.txt` + versioned `.md` in `fs_store._write_prompt`); approval modal shows question-agent prompt diffs (`kind: question_agent` in `promotion_preview` + `PromotionReviewModal`).

Extra test fallout from Round 2 (mostly resolved): pipeline/workflow node-list expectations; `AppealPackage.question_interview`; coordinator seed includes `question_agent_system_prompt` + `geo_playbook:us`; offline `run_evaluated_case(..., run_question_agent=True)` may log Gemini-fallback warnings with stub clients — harmless.

## What was built (files)

Backend — new:
- `backend/app/aegis_v1/question_agent.py` — adaptive interview core (Protocol + Stub + Gemini). Evolvable component id pinned: `question_agent_system_prompt`.
- `backend/app/aegis_v1/patient_simulator.py` — showcase-only patient sim; refuses regulatory questions.
- `backend/app/aegis_v1/question_workflow.py` — `run_pre_draft_interview` (showcase/eval orchestration seam).
- `backend/app/aegis_v1/question_session.py` — turn-based in-memory sessions for `/appeal` (start/answer/skip). In-memory by design; Redis/DB if API goes multi-worker.
- `backend/app/aegis_v1/prompts/question_agent_v1.md` — system prompt.
- `backend/app/evals/part_a/question_judge.py` — deterministic question judge: Part A conversation quality (1/3/5), Part B append-first `playbook_additions`. Replaces the score-5 stub.

Backend — edited:
- `backend/app/aegis_v1/schemas.py` — `QATurn`, `QuestionInterviewResult`.
- `backend/app/aegis_v1/appeal_api.py` — `POST /v1/appeal/questions/start`, `/{id}/answer`, `/{id}/skip`; `AppealRequest.interview_id`; `AppealResponse.question_interview` (internal_gap_analysis + enriched_context excluded from the wire response).
- `backend/app/aegis_v1/appeal_orchestrator.py`, `backend/app/evals/part_a/evaluated_run.py`, `backend/app/evals/part_a/measurement_run.py` — opt-in `run_question_agent` wiring; interview runs pre-draft, drafter receives only enriched patient-knowable context; `question_interview` threaded into `run_panel`.
- `backend/app/evals/part_a/panel.py` — `STUBBED_QUALITY_DIMENSIONS` removed; real judge wired into offline + ADK paths; `question_graded` / `question_playbook_additions` in panel metadata.
- `backend/app/aegis_v1/geo_playbook.py`, `geo_playbooks/us_playbook.json` — US-playbook loader, case filtering, question-agent prep bundle.
- `backend/app/aegis_v1/promotion_preview.py` — approval diffs for drafter, question agent, slice playbooks, and US-playbook rules.
- `backend/app/learning/coordinator.py` — `question_agent_system_prompt` + `geo_playbook:us` registered as evolvable components (eligible ids, seed candidate, global slice filter).
- `backend/app/learning/fs_store.py` — promotes slice playbooks, US playbook file, and runtime prompt pointers (`active_drafter_prompt.txt`, `active_question_agent_prompt.txt`).
- `backend/app/learning/reflection_client.py` — append-first playbook rules; question-judge recs routed to slice playbooks vs US-playbook by rec wording (`add to playbook` vs `add to global playbook`).
- `backend/app/aegis_v1/student_workflow.py` — `geo_playbook_loader_node`, `geo_playbook` on drafter prep, US rules in question-agent node prep.

Frontend — new:
- `frontend/src/components/flow/QuestionChat.tsx` — chat step on `/appeal` (answer / "I don't know" / skip; fails soft to drafting if the API is down).

Frontend — edited:
- `frontend/src/lib/types.ts`, `lib/schema.ts` — `QATurn`, `QuestionInterview`, `QuestionTurn`, `interview_id` on request, `question_interview` on response (zod drops unknown/internal fields).
- `frontend/src/lib/promotionPreview.ts`, `components/showcase/console/PromotionReviewModal.tsx` — `question_agent` section in showcase approval modal (text diff, same as drafter).
- `frontend/src/lib/data/source.ts`, `data/live.ts`, `data/demo.ts`, `data/index.ts` — `startQuestions`/`answerQuestion`/`skipQuestions` (live = real endpoints; demo = 2 canned questions).
- `frontend/src/lib/flow/reducer.ts` — new `questions` step + `BEGIN_QUESTIONS` action (existing `SUBMIT` semantics unchanged, so old reducer tests should still pass).
- `frontend/src/app/appeal/page.tsx` — intake → questions → working → mirror → draft → decide.
- `frontend/src/components/flow/DraftEditor.tsx` — "From your Q&A" gap-note rail section.

## Tests to run (in order)

### 1. Backend — new/feature tests first
From `backend/`:
```
uv run pytest tests/unit/aegis_v1/test_question_agent.py tests/unit/aegis_v1/test_question_firewall.py tests/unit/evals/test_question_judge.py -v
```
- All three files pass in the verified suite.
- `test_question_firewall.py` holds the INV-QA build-breaking tests + session flow tests.

### 2. Backend — regression on touched areas
```
uv run pytest tests/unit/evals/test_evaluated_run.py tests/unit/evals/test_part_a_judge_panel.py tests/unit/evals/test_measurement_run.py tests/unit/evals/test_firewall.py tests/unit/evals/test_judge_workflow_phase3.py -v
uv run pytest tests/unit/aegis_v1/test_appeal_route.py tests/unit/aegis_v1/test_appeal_orchestrator.py tests/unit/aegis_v1/test_appeal_best_of_five.py -v
uv run pytest tests/unit/learning/test_coordinator.py tests/unit/learning/test_integration.py tests/unit/learning/test_efficacy_harness.py -v
uv run pytest tests/unit/aegis_v1/test_geo_playbook.py tests/unit/aegis_v1/test_promotion_preview.py tests/unit/learning/test_promotion_wiring.py -v
```
Historical fallout (mostly fixed):
- Any test referencing the removed `panel.STUBBED_QUALITY_DIMENSIONS` or the old stub reasoning text ("Question agent not yet implemented…"). The replacement behavior: no interview → score 5, `graded=False`, reasoning mentions "traced, not graded".
- Coordinator tests asserting the exact component set of the seed candidate (now includes `question_agent_system_prompt`) or round-robin order (`select_component` sorts ids; the new id changes the rotation). Update expectations — the new component is intentional.
- Coordinator seed now reads the question prompt file via `load_question_agent_prompt()`; if a test uses a fake store without `list_prompt_versions` for that id, it falls back to disk (file exists in repo, should be fine).
- `test_appeal_route.py`: `AppealResponse` gained an optional `question_interview` field (default `None`) — should be backward compatible.

### 3. Backend — full suite
```
uv run pytest tests/unit -q
```
Last verified: **446 passed, 0 failed** (from `backend/`). Use `uv run`, not bare `python -m pytest` (ADK import path).

### 4. Frontend
From `frontend/`:
```
npx vitest run
npx tsc --noEmit
npm run lint
```
Known issue, NOT caused by this work: `src/__tests__/statusPreviewBatch.test.ts` has 8 pre-existing TS errors (missing `patient_age`/`patient_gender` on `CaseSummary` literals, missing `ShowcaseRunDiagnostics` fields, a duplicate object key). `tsc --noEmit` was run after the question-agent frontend changes and these were the ONLY errors — none in the new/edited files. Fix or skip per your judgment; they belong to the showcase status work.
- `reducer.test.ts` should pass unchanged (SUBMIT still → `working`). Consider ADDING cases for `BEGIN_QUESTIONS` → `questions`.

### 5. Manual smoke (optional but recommended)
1. Start backend (FastAPI app `app/main_v1.py`) and `npm run dev` in `frontend/`.
2. `/appeal`: paste a denial → intake → chat step appears → answer 1–2 questions, "I don't know" one, then let it finish (or Skip). Draft page should show the letter + "From your Q&A" gap note in the rail.
3. Kill the backend mid-chat → the step should fail soft and offer "Continue to the draft".
4. Showcase path: `run_evaluated_case(..., run_question_agent=True)` with stub clients (StubDrafterClient + StubPatientSimulatorClient + StubQuestionAgentClient via `question_agent_client`) — confirm `EvaluatedRun.question_interview` is populated (now sourced from `appeal_package["question_interview"]`, i.e. the workflow node ran), panel metadata has `question_graded: true`, and with a regulatory sentence in the case's `clinical_context` the metadata's `question_playbook_additions` contains "Add to playbook:"/"Add to global playbook" instructions.
5. Live showcase run (quick run from the showcase UI): training + measurement now interview every case; check Phoenix annotations carry `question_turn_count` tags and the question-judge additions in `judge_metadata`.

## Deferred / follow-ups (do not block on these)
- Showcase rollback stack still snapshots only the **drafter** active prompt pointer — not `active_question_agent_prompt.txt` or US-playbook file. Extend `showcase_rollback.py` if one-click rollback must restore question-agent / geo promotions too.
- `PATIENT_UNSURE` ("I'm not totally sure…") currently counts as a substantive answer in `is_substantive_answer` (substring quirk). Harmless but worth a small fix + test.
- Question session store is per-process; fine for the demo, swap for Redis if the API scales out.
- Frontend `statusPreviewBatch.test.ts` — 8 pre-existing `tsc` errors (unrelated to question agent).
