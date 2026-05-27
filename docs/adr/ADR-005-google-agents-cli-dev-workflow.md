# ADR-005: Adopt `google-agents-cli` for backend dev lifecycle

**Date:** 2026-05-27 (Session 3)
**Status:** Accepted
**Mode:** CONTEMPORANEOUS to Session 3.

## Context

`google-agents-cli` was released by Google in April 2026 as the unified developer-lifecycle CLI for the ADK ecosystem. It is **built on top of Google ADK**, not a replacement for it — agents are still built with ADK Python API; `agents-cli` handles project scaffolding, evaluation harnesses, deployment to Cloud Run / Agent Runtime / GKE, observability wiring, and Gemini Enterprise publishing. It ships as a `uvx`-installable package that also bundles 7 skills that drop into any coding agent with skills support (Gemini CLI, Claude Code, Codex, Antigravity, etc.).

Aegis is built by a non-technical PM in a 20-day window, using Amp + Cursor + the existing repo skill library. Day 1 setup time is precious: signing up for Phoenix Cloud, configuring Google Cloud, scaffolding the ADK project, wiring instrumentation, and verifying the Phoenix-MCP-load-bearing integration spike (assumption A4) all need to happen the same day. Hand-built scaffolding and deployment scripts would consume disproportionate time.

The 7 bundled skills cover real gaps in the existing skill library:
- `google-agents-cli-workflow` (development lifecycle, code preservation, model selection)
- `google-agents-cli-adk-code` (ADK Python API — agents, tools, orchestration, callbacks)
- `google-agents-cli-scaffold` (project scaffolding — `create`, `enhance`, `upgrade`)
- `google-agents-cli-eval` (evaluation — metrics, evalsets, LLM-as-judge)
- `google-agents-cli-deploy` (deployment — Agent Runtime, Cloud Run, GKE, CI/CD)
- `google-agents-cli-publish` (Gemini Enterprise registration)
- `google-agents-cli-observability` (Cloud Trace, logging, third-party integrations)

## Decision

**Install `uvx google-agents-cli setup` on Day 1 of the build window. Use its `create` / `playground` / `eval` / `deploy` commands and its 7 bundled skills for the full ADK lifecycle. Keep ADK as the framework (see [ADR-001](ADR-001-google-adk-agent-framework.md)).**

Skill routing rule (codified in [root AGENTS.md → Orchestration Map](../../AGENTS.md)):
- ADK-specific work (scaffold, eval, deploy, ADK Python API, observability) → `google-agents-cli-*` skills.
- Framework-agnostic process work (TDD, code review, architecture decisions, brainstorming, assumption mapping) → existing skill library.
- Deconflict overlaps as they surface during build.

## Alternatives Considered

- **Skill-only install (`npx skills add google/agents-cli`):** Get the 7 skills, skip the CLI commands. Rejected: gives up the `create` / `playground` / `eval` / `deploy` leverage. CLI is the bigger win.
- **Defer adoption to a Day 1 review:** Wait until after the Day 1 Phoenix-MCP spike to decide. Rejected: Day 1 time is precious; the scaffolding leverage IS what we need on Day 1.
- **Don't adopt; build scaffolding/deploy manually:** Lowest risk of skill conflict. Rejected: reinvents wheels Google has already built; consumes solo-PM time disproportionately.
- **Agent Starter Pack (predecessor):** The pre-`agents-cli` Google scaffolding tool. Rejected: superseded by `agents-cli` per the [official migration guide](https://google.github.io/agents-cli/reference/from-agent-starter-pack/).

## Consequences

- ✓ Day 1 setup compresses from "hand-build scaffold + custom deploy script + custom eval harness" to "`agents-cli create my-agent` + `agents-cli deploy` + `agents-cli eval`".
- ✓ ADK Python API knowledge is fed into the coding agent via skills, reducing context-window waste during agent code generation.
- ✓ `agents-cli playground` provides a local ADK web playground with hot reload — useful for testing agents before the Next.js frontend exists.
- ✓ First-party Google tooling — current and maintained; minor version bumps add features rather than breaking changes.
- ⚠ **Observability skill conflict risk.** `google-agents-cli-observability` emphasizes Cloud Trace. We use Phoenix as primary observability. Open question [J1](../open-questions.md) — Day 1 spike must verify the two coexist or skip the agents-cli observability skill.
- ⚠ **Deploy skill ↔ 2-service Cloud Run topology.** `google-agents-cli-deploy` assumes single-service Agent Runtime patterns. Open question [J2](../open-questions.md) — Day 6–7 verification before MVP deploy. If incompatible, use agents-cli for backend only; custom script for Next.js frontend.
- ⚠ **Skill library overlap.** Our existing library has `test-driven-development`, `eval-output` chain, `code-review-crsp`, etc. that overlap with agents-cli's `eval` and `workflow` skills. Skill routing rule in AGENTS.md mitigates; deconflict explicitly when both fire on the same task.
- ⚠ **Native Windows not officially supported.** PM is on macOS/Linux/WSL2 — not an issue.
- ⚠ **Vendor lock-in.** Switching off agents-cli post-hackathon would require replacing scaffold + deploy + eval scripts. Acceptable for hackathon; matches the existing ADK lock-in.

## Revisit triggers

- `google-agents-cli-observability` skill conflicts with Phoenix MCP setup on Day 1 → skip that specific skill; keep Phoenix as primary observability.
- `google-agents-cli deploy` cannot handle 2-service Cloud Run topology → use it for backend only; write custom deploy script for frontend.
- Breaking changes in `agents-cli` versions during the 20-day window → pin to working version in `pyproject.toml`.
- If any of the 7 bundled skills produces outputs that contradict our existing skill outputs (e.g. eval rubric design), our `eval-output` chain wins; agents-cli skill output is treated as a starting draft.

## References

- agents-cli getting started — https://google.github.io/agents-cli/guide/getting-started/
- Google announcement, Apr 2026 — https://developers.googleblog.com/agents-cli-in-agent-platform-create-to-production-in-one-cli/
- agents-cli GitHub — https://github.com/google/agents-cli
- Session 3 decision in [docs/memory/decision-log.md](../memory/decision-log.md)
- Open questions J1 + J2 in [docs/open-questions.md](../open-questions.md)
