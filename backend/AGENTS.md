# Backend — Agent Rules

See root [AGENTS.md](../AGENTS.md) for project-wide context, PM working-agreement, safety/tone rules, scope constraints, and the Orchestration Map. This file is **backend-specific** only.

## What lives here

Python service hosting the Google ADK agent(s) + the offline learning job + the eval pipeline. Exposes a FastAPI endpoint consumed by the Next.js frontend. Deployed as its own Cloud Run service.

Part A: one ADK agent. Part B: 12-agent swarm + Learning Coordinator (see PRD §12). Build Part A first.

## Stack

| Layer | Tool | Note |
|---|---|---|
| Runtime | Python 3.11 | ADK requirement |
| Package manager | `uv` | Faster than pip/poetry |
| API server | FastAPI | Only public surface the frontend calls |
| Agent framework | Google ADK | Hackathon Arize-track requirement |
| Dev workflow CLI | `google-agents-cli` (`uvx google-agents-cli setup`) | Scaffold, eval, deploy, observability. Bundles 7 skills into the coding agent. |
| LLM | Gemini 3 (fallback: 2.5) | Via Google GenAI SDK / ADK |
| Tracing | `openinference-instrumentation-google-adk` | Auto-instrument every agent call |
| MCP | `@arizeai/phoenix-mcp` (npx) | Configured as ADK tool source |
| Retrieval | BM25 (`rank_bm25`) over local markdown | No vector DB |
| Tests | pytest | Unit + integration |

## Non-obvious patterns

- **Phoenix MCP is load-bearing, not decorative.** The agent's quality must visibly degrade if MCP is disabled — that's the demo counterfactual. Don't write code paths that work fine without it.
- **`google-agents-cli` is the project's dev backbone.** Use `agents-cli create`, `agents-cli playground`, `agents-cli eval`, `agents-cli deploy` instead of writing custom scaffolding/eval/deploy scripts. Skills are bundled and visible via `/skills`.
- **agents-cli observability vs Phoenix MCP** — agents-cli's observability skill emphasizes Cloud Trace. We use Phoenix. Sanity-check on Day 1 that both can coexist; prefer Phoenix as primary, Cloud Trace as secondary if helpful.
- **Every run produces a complete Phoenix trace with full metadata** (case_id, insurer, denial_type, plan_type, state, prompt_version, playbook_version, dataset_split, run_mode). Trace fidelity is an explicit NFR (PRD NFR4).
- **Strict JSON output** for all LLM tool calls (`response_mime_type=application/json`). Pydantic models in `src/agent/schemas.py` are the schema source of truth.
- **Self-check pass before returning.** Every appeal package goes through `self_check_appeal` — verifies each citation traces to the corpus, no invented statutes, facts match input. Surface failures as `risk_flags`, log to Phoenix.
- **Playbooks are git-tracked JSON** in `playbooks/<insurer>__<denial_type>.json`. Versioned. Promoted playbooks are immutable — never overwrite, bump version.
- **Prompts are versioned** in `src/prompts/` AND registered as Phoenix Prompts. Bump version on every promotion.
- **ADK multi-agent patterns reference:** [Google's official 8-pattern guide](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/). Part B uses a Composite Pattern (Coordinator + Parallel Fan-Out + Sequential + Generator-Critic + Iterative Refinement + Human-in-the-loop).

## Phoenix configuration

- Project name: `aegis-hackathon`
- Datasets: `benchmark_train_v1`, `benchmark_holdout_v1`, expanding to v2/v3 as benchmark grows.
- API key in `.env` (`PHOENIX_API_KEY`); never hardcoded.
- MCP server config goes in agent runtime, not user environment — see `docs/architecture.md` §6.2 *(needs Session 2 update)*.

## Safety (backend-specific reinforcement of root rules)

- **PHI scan on every commit.** Pre-commit hook checks for SSN, MRN, DOB patterns, real-sounding names + ICD/CPT combinations. Reject commits that fail.
- **No real denial letters in `eval/cases/`.** Only synthetic composites with provenance traced in `eval/dataset_card.md`.
- **Sanitize before logging.** If you log raw user input anywhere, run the PHI sanitizer first.
- **Trace metadata is safe to log.** Trace content (the appeal letter itself) is safe in Phoenix because it's synthetic-case-derived. Live user PHI never enters this system — there is no live-user path in scope.

## Code style

- Type hints everywhere (`from __future__ import annotations`).
- Pydantic v2 for all schemas.
- Functions > classes when state isn't needed.
- One tool per file in `src/agent/tools/`; each tool is a pure function with explicit input/output Pydantic schemas.
- Tests next to source: `src/agent/tools/foo.py` ↔ `tests/unit/agent/tools/test_foo.py`.

## Boundaries

- **Ask first:** new LLM model choice, new vendor/service, autonomy threshold changes, new prompt versions promoted to "current", agent architecture changes (adding/removing agents in the swarm).
- **Full autonomy:** test writing, internal refactors that don't change agent behaviour, lint/format/typecheck fixes, dependency version bumps within the same major version.
- **Never:** log PHI (there shouldn't be any, but assume there could be), invent statutes or policy text, write a code path that hides the Phoenix MCP dependency, claim "wins X% of appeals" — only "simulated wins on synthetic benchmark".

## Skills most relevant here

**ADK-specific (via `google-agents-cli`):** `google-agents-cli-workflow` · `google-agents-cli-adk-code` · `google-agents-cli-scaffold` · `google-agents-cli-eval` · `google-agents-cli-deploy` · `google-agents-cli-observability`.

**Framework-agnostic:** `agent-system-architecture` · `agent-builder` · `create-agent-prompt` · `tool-finder` · `architectural-decision-log` · `eval-output` chain (`eval-rubric-design` · `eval-judge` · `eval-pipeline`) · `test-driven-development` · `debug-and-fix` · `code-review-crsp`.

## Eval discipline

`eval/` is the load-bearing artifact for the Arize submission. Per root AGENTS.md → Build Discipline:
- All cases are synthetic composites with provenance.
- The rubric, judges, and pipeline are designed via the `eval-output` skill chain — they must be AlphaEval-compliant (independent dimensions, safety + hallucination as binary hard gates, chain-of-thought judge protocol, bias mitigation).
- Per-step (per-agent) evals for the Part B swarm — not just end-to-end composite.
- `google-agents-cli-eval` can run the eval harness on demand; use it for fast iteration, but the source-of-truth rubric is owned by our `eval-output` skill chain output (`docs/evals/rubric.md`).
