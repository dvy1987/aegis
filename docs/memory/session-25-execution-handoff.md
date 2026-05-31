# Session 25 — Execution Handoff: Tier 2 (offline efficacy) + Tier 1 (live GCP/Phoenix)

**Created:** 2026-05-31 (end of Session 24). **Read this first if you are a fresh/compacted session.**

---

## Where things stand (end of Session 24)

The Learning Coordinator is **built and proven offline**:
- **Phase 1 (done):** the full GEPA-faithful coordinator package `backend/app/learning/` (models, store, signal+firewall, reflection, selection, mutation, merge, gates, experiment, coordinator, efficacy_harness). 12 TDD tasks, learning suite 35 / full unit **90 passed**. Commits `9f048f7..53f1eaf`.
- **Phase 2 (done):** assistant-orchestrated efficacy Run #1 — the **Claude session itself was the drafter/judge/reflection intelligence** (no API key) over the real synthetic cases. Optimized the Student drafter prompt for `appeal_vector_capture`: **held-out 0.73 → 0.88 = +0.15 / +20.5%**, firewall intact, promoted `drafter_v2`. Captured under `eval/efficacy_runs/2026-05-31/` + replay regression `backend/tests/unit/learning/test_efficacy_run_fixture.py`. Evidence: `docs/evals/2026-05-31-coordinator-efficacy-run.md`. Commits `2c21d33`, `96a5cf7`.

Two plans are now written and ready to execute (this session's deliverable):
1. **Tier 2 — offline, executable NOW (no creds):** `docs/plans/2026-05-31-learning-efficacy-tier2-offline-plan.md`
2. **Tier 1 — live GCP/Phoenix, credential-gated:** `docs/plans/2026-05-31-learning-coordinator-live-gcp-companion-plan.md`

---

## Recommended order

**Do Tier 2 first** — it needs nothing but this repo, hardens the efficacy story, and produces the reusable `efficacy_io` module that Tier 1's live harness also uses. **Then Tier 1**, on the machine where GCP ADC + `PHOENIX_API_KEY` are configured.

### Tier 2 (offline) — how to run
- **Task 1 is pure TDD** (extract `efficacy_io`, tested against the committed Run #1 fixtures) — do it subagent-driven exactly like Phase 1.
- **Tasks 2–3 are subagent-orchestrated runbooks** (round 2 on the full 10/10 split; reflection meta-prompt A/B). The Claude session plays drafter/judge/reflection again. **Reuse Run #1's discipline verbatim:**
  - Firewall: drafter/reflection subagents get only `build_student_case_packet` output; only judge subagents get the teacher packet; reflection notes stay laundered.
  - Judge calibration: **1/3/5 only (never 2/4)**, anchor 5 reserved, `appeal_vector_capture`/`case_specific_clinical_rebuttal` scored against the teacher's *specific* vectors, coherence penalizes padding. (This was the key fix in Run #1 — without it the strong base model grades near-ceiling and there's no measurable headroom.)
  - Fixed safety harness on every draft (disclaimer verbatim, no win-claims, draft-only, no government-program framing, no exclamation, facts-only, no invented authorities, no corpus/playbook) — a constant across versions.
  - **Honest-result clause:** if the full split shows v2 already at the offline ceiling (every promptable dim ≈5; only corpus-bound `grounding` low), RECORD THAT — do not manufacture lift. Real headroom for `grounding` needs live corpus (Tier 1).

### Tier 1 (live) — how to run
- **The offline cores build anywhere** (Task 1 `PanelJudgeAdapter`; the pure transforms in Tasks 2/3/5/6) — do those subagent-driven with their unit tests, green, even here.
- **Task 0 (resolve Phoenix MCP auth) is the critical path and a prereq for the live parts.** The `backend/test_mcp_standalone.py` spike connects but `list-traces` hit an Arize-cloud auth/version error; fix `PHOENIX_CLIENT_HEADERS`/`PHOENIX_API_KEY`, confirm `get-spans`, and **record the real payloads as fixtures** (`backend/tests/fixtures/phoenix/`) — those fixtures pin the offline transform tests forever. If MCP auth can't be settled, fall back to the Phoenix **client** (`px.Client()`, already used by `OtelPhoenixRecorder.annotate`) for reads; the transforms are identical, only the fetch wrapper changes.
- Live behavior is exercised only by `tests/integration/test_live_*.py` behind a `_creds_available()` skip-guard (mirror `_adc_available()` in `test_live_appeal.py`). Cloud/SDK imports stay method-local.

---

## Why these two, and what they unlock
- **Tier 1 is the actual submission thesis.** "Phoenix MCP is structurally load-bearing — toggle it off, quality collapses." Today `phoenix_mcp_lookup` is a hardcoded stub, so that demo can't run. Tier 1 makes it real (T4.1), implements the live `PhoenixLearningStore`, wires the coordinator to live Gemini + live Phoenix signal, and **captures the MCP-off counterfactual** (Task 5) — the money shot — plus a κ≥0.6-calibrated judge (Task 6).
- **Tier 2 is the cheapest way to deepen the "it improves" evidence** before creds exist, and its `efficacy_io` module is shared infrastructure.
- The **Tier-2-optimized prompts (`drafter_v2`/`v3`) are the seed components for the live loop** — Tier 1 re-runs the same optimization with Gemini + an independent judge and treats the offline prompts as the starting point.

---

## Hard constraints & gotchas (tell every subagent)
- **No GCP/Gemini/ADC, no `ANTHROPIC_API_KEY` on this machine.** Tier 2 is fully offline. Tier 1's offline cores are testable here; its live smoke tests skip cleanly. Never attempt a live call in a non-gated test.
- **Test command (from `backend/`):** `env UV_CACHE_DIR=/tmp/uv-cache uv run pytest <path> -q`.
- `git commit` from repo root; commit per task; every message ends with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`. Nothing pushed to `origin` unless asked.
- **Firewall (INV-2)** is enforced in code (`signal._launder`, `recorder.laundered_signal`) AND must be respected by hand in the runbook tasks. Do not enumerate answer-key field names even in reflection meta-docs (Run #1 had to fix this — `test_efficacy_run_fixture.py` scans for it).
- **INV-1:** the coordinator reads its gradient only via `PhoenixLearningStore`; empty signal → no promotable candidate (tested). **INV-3:** optimize the judge composite, never the insurer APPROVE/DENY; never promote an APPROVE-with-failing-hard-gate.
- **Cloud/SDK imports stay method-local** (the `GeminiDrafterClient`/`OtelPhoenixRecorder` pattern) so `import app.*` and the offline suite stay clean.

## Acceptance (done-when) — quick reference
- **Tier 2:** `efficacy_io` tested + Run #1 scripts DRY'd (result.json unchanged); round 2 ran on the full 10/10 split (promoted `drafter_v3` with recorded lift OR honest "ceiling reached"); meta-prompt A/B has a recorded winner/tie; replay regression covers round 2; `tests/unit` green.
- **Tier 1:** offline cores green anywhere; on the credentialed box — live `phoenix_mcp_lookup`, live `read_scored_runs` (firewall intact), `run_live.py` produces a `PromotionProposal` from live Gemini + Phoenix, the MCP-off counterfactual shows a measured drop, judge κ≥0.6. INV-1/2/3 hold live.

## Pointers
- Cold-start read order: `orientation-map.md` → `current-state.md` (Session 24 entries) → the two plan files above → the v2 spec (`docs/specs/2026-05-31-learning-coordinator-v2-gepa-design.md`) §2 + §7.
- Prior handoff: `session-24-execution-handoff.md` (the manual-GEPA runbook + firewall table this all builds on).
