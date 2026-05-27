# Plan: Evolve the Case Generator Swarm — Harness Orchestration + Claude-on-Vertex Critic

**Status:** Drafted 2026-05-27 (end of Session 10). Awaiting next-session execution.
**Owner agent:** next session.
**Prereq:** Session 10 left a working Vertex-backed Python case_generator at `backend/app/case_generator/`. This plan extends it; nothing is being thrown away.

## Why this plan exists

End of Session 10, PM raised three observations that reframe the swarm's architecture:

1. The drafter and critic in the current build are both `gemini-3.1-pro-preview` — same family. AlphaEval principles + backend AGENTS.md say critics should be a different model family than drafters.
2. The Droid harness has a `Task` tool that can spawn worker subagents. We don't need to roll our own LLM-call backend — the harness can BE the LLM orchestrator.
3. Phoenix tracing is not needed for offline synthetic case generation. (It matters for the runtime appeal agent and the Learning Coordinator, neither of which is this swarm.)

This plan converts these observations into concrete work for the next session.

## Goals (in order)

1. **G1 — Different model family for critics on the existing Vertex path.** Wire Claude Opus 4.7 (or Claude Sonnet 4.7) on Vertex AI as the critic model. Gemini stays as the producer model. This is the single highest-leverage change for AlphaEval rigour.
2. **G2 — Add a harness-Task orchestration path (optional toggle).** Reuse all 21 prompt templates. The harness becomes the orchestrator; each producer + critic becomes a `Task` subagent. Parallelise the 9-critic final-assembly panel.
3. **G3 — Keep the Vertex-Python path as the autonomous batch runner.** It is the path that can produce 10–100 cases unattended overnight. Do not delete it.

## Non-goals

- Phoenix tracing for the generator (PM confirmed: not needed for offline generation).
- ADK Runner / Session integration (overkill for a batch tool).
- Rewriting the existing prompts (they are already AlphaEval-shaped and validated by a successful smoke run).
- Building a generic LLM-abstraction layer for the whole backend. Scope this work to `backend/app/case_generator/`.

---

## G1 — Claude-on-Vertex critic (highest-priority work)

### Background — Claude on Vertex AI Model Garden

Anthropic models are first-class on Vertex AI Model Garden in the `us-east5` / `europe-west1` regions (subject to allow-listing per region — check Model Garden enablement in `gen-lang-client-0362343014` before coding). Vertex AI uses Anthropic's `AnthropicVertex` SDK client which authenticates via Application Default Credentials (already configured in this project, no new keys needed). Model identifiers look like `claude-opus-4-1@20251101` / `claude-sonnet-4-1@20251101` etc. Choose the latest stable Opus version available in the project's region at session start.

References to verify at session start (must do BEFORE coding):
- `gcloud ai models list --region=us-east5 --filter="publisher_model.name:anthropic*"` to see what is enabled in our project.
- Anthropic Vertex SDK docs (canonical: https://docs.anthropic.com/en/api/claude-on-vertex-ai). Confirm the exact `model=` string for the current Opus version.
- Verify Model Garden enablement in the Cloud Console under "Vertex AI → Model Garden → Anthropic Claude" — accept terms if not yet accepted.

### Implementation

1. **Add dependency.** Append to `backend/pyproject.toml`:
   ```toml
   "anthropic[vertex]>=0.40.0,<1.0.0",
   ```
   Run `uv lock` to update `uv.lock`.

2. **Add a CriticBackend abstraction in `agents.py`.** Two backends:
   - `GeminiBackend` (current) — `google.genai.Client` via Vertex, model `gemini-3.1-pro-preview`.
   - `ClaudeVertexBackend` (new) — `anthropic.AnthropicVertex` client with explicit `project_id=GOOGLE_CLOUD_PROJECT`, `region="us-east5"` (or whichever region the project has Claude enabled), model from env `AEGIS_CASEGEN_CRITIC_MODEL` (default `claude-opus-4-1@latest-stable`).
   - Both backends must return parsed JSON dicts to keep the call sites identical.
   - Force JSON output: Anthropic Vertex supports a system-prompt directive to emit JSON only (no `response_mime_type` like Gemini). Use a small `system="You output ONLY raw JSON…"` and `messages=[{role:"user", content:prompt}]`. Strip any accidental markdown fences before `json.loads`.

3. **Route by critic-vs-producer.** Producers stay on `GeminiBackend`. Critics switch to `ClaudeVertexBackend`. The existing `AEGIS_CASEGEN_CRITIC_MODEL` env var becomes the Claude model id; `AEGIS_CASEGEN_MODEL` stays as the Gemini producer id.

4. **Schema robustness.** Claude Vertex sometimes returns prose preamble before the JSON. Add a `_extract_json(text)` helper that finds the outermost `{...}` block and parses it. Apply to both backends defensively.

5. **Smoke test.** Re-run the 1-case smoke from Session 10 (`--count 1 --split test --seed 7`). Expected change: critic_verdicts JSON now shows critic outputs that read distinctly different from the Gemini-style critic outputs already captured in `case_01_aetna_priorauth.json`. Look at `synthetic_provenance.critic_verdicts.*.reasoning` strings — Claude's CoT shape will differ.

6. **Cost note.** Claude Opus on Vertex is meaningfully more expensive per token than Gemini. Each case has 16 critic calls; estimate ~$0.30–$0.60 per case at Opus pricing. Document the per-case cost in the handoff after the smoke run. If too high for a 10-case batch (~$3–$6 per benchmark refresh), fall back to `claude-sonnet-4-1` for routine batches and reserve Opus for the official Day 5 benchmark.

### Acceptance criteria for G1

- [ ] `anthropic[vertex]` installed and importable.
- [ ] Critic backend toggled by env var; default is Claude on Vertex.
- [ ] Smoke run completes 1 case end-to-end, schema-valid, all 19 critic verdicts captured.
- [ ] Cost-per-case logged in handoff for both Opus and Sonnet.
- [ ] `synthetic_provenance.critic_verdicts.*.dimension` now reflects critic identity AND critic model id; provenance schema bumped to `1.1.0` to add a `critic_model` field per verdict.

---

## G2 — Harness-Task orchestrator (optional path)

This path turns the swarm into a harness-driven runbook. Implementation is intentionally light — most of the work is already done (the prompts).

### Shape

- A new top-level skill or runbook file: `docs/runbooks/2026-05-28-case-generator-harness-runbook.md` — step-by-step instructions for a coding agent to drive the swarm using `Task` calls.
- A small Python helper `backend/app/case_generator/harness_io.py` that:
  - Reads `eval/diversity_matrix.json` and emits one sampled matrix cell to stdout (the harness then puts it into a prompt).
  - Validates an assembled case JSON against `eval/case_schema.json` and writes it to `eval/cases/drafts/part-a/{split}/<case_id>.json`.
  - Computes `case_id` and the next free index.

The agent's flow becomes:
1. Run `python -m app.case_generator.harness_io sample-cell` → get a matrix cell.
2. Render the planner prompt with the cell, spawn `Task(subagent_type="worker", description="ScenarioPlanner", prompt=…)`.
3. Spawn the 2 stage critics in parallel.
4. If hard-gate fail → loop back to step 1; if weighted=1 → respawn the planner with revision instructions.
5. Continue per-stage: drafter → 2 critics; writer → 2 critics; diversifier → 1 critic; safety+schema (deterministic); final 9-critic mini-panel (parallel).
6. Assemble case JSON + `synthetic_provenance` (run_id, prompt_versions, critic_verdicts, model_used).
7. Run `python -m app.case_generator.harness_io write-case '<json>' --split <split>`.

### Pros and cons (recap from Session 10)

| Pro | Con |
|---|---|
| Uses Claude Opus 4.7 (harness model) for both producer + critic — different family from production Gemini agent. | Slower wall-clock (Task spawns are not optimised for 20+ calls). |
| Zero Vertex spend; uses harness subscription. | ~20 round-trips per case clutter the agent conversation. |
| Parallelism free: 9 final-panel critics in one assistant message. | Same-model drafter + critic violates AlphaEval different-family principle WITHIN the swarm (G1 fixes this on the Vertex path; harness path can't). |
| Auditable: every prompt + response is visible in the chat. | Hard to run unattended overnight. |

### Acceptance criteria for G2

- [ ] `harness_io.py` exists and supports `sample-cell` + `write-case`.
- [ ] Runbook exists with explicit Task-tool examples for each stage.
- [ ] One case generated via this path end-to-end and verified schema-valid.

---

## G3 — Keep Vertex-Python path

- Do not delete or break the current CLI.
- Update `eval/dataset_card.md` to document BOTH paths once G1 is done.
- Decision rule for which path to use:
  - Need ≥ 5 cases or running overnight → Vertex-Python.
  - Need 1–2 cases inside a working session and want to eyeball every step → harness-Task.

---

## Estimated effort

| Item | Effort |
|---|---|
| G1 (Claude-on-Vertex critic) | 60–90 min |
| G1 smoke test + cost log | 30 min |
| G2 (`harness_io.py` + runbook) | 60–90 min |
| G2 one-case validation | 30 min |
| Update dataset_card + handoff | 15 min |
| **Total** | **3–4 hours** |

## Open questions to resolve at session start

1. Is Claude enabled in our Vertex project + which region (`us-east5` vs `europe-west1`)? Run `gcloud ai models list --region=us-east5 --filter=anthropic` first thing.
2. Is the cost-per-case at Opus acceptable for routine 10-case batches, or do we use Sonnet for routine and Opus for official benchmarks only?
3. Should the harness-Task path emit a `critic_model: "claude-opus-via-harness"` in provenance so audit trails distinguish from Vertex-Claude?

## Out of scope (defer further)

- Multi-model critic ensembles (Claude AND GPT both vote — interesting but expensive; revisit Day 12+).
- Phoenix tracing of generator runs.
- Auto-promotion from `drafts/` to `approved/` (Gumloop swarm remains the gate).
