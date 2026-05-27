# ADR-004: Part B uses a 12-agent composite swarm (NOT compressed to lean 5-agent topology)

**Date:** 2026-05-27 (Session 3)
**Status:** Accepted with explicit revisit triggers
**Mode:** CONTEMPORANEOUS to Session 3.

## Context

PRD §12 specifies Part B as a "12-agent swarm" — Orchestrator, Triage, Insurer Intelligence, Policy Detective, Medical Necessity Researcher, Legal Researcher, Precedent Miner, Strategist, Drafter, Adversarial Reviewer, Quality Judge Panel, Outcome Simulator — plus Learning Coordinator and Pattern Synthesizer as meta-agents (14 total components).

In Session 3, this architecture was critically evaluated against:
1. [Google's official 8-pattern multi-agent guide for ADK](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) (Dec 2025)
2. Build-time math for a non-technical solo PM in a 20-day window
3. Demo-coherence test for the 3-minute submission video
4. Arize judging rubric (which rewards loop quality, not agent count)

The critique surfaced five rough edges:
- (1) The "12" count includes evals miscounted as agents (Quality Judge Panel is 7 LLM-as-judge graders, not 1 agent; Outcome Simulator is a deterministic rule engine + 1 LLM call).
- (2) The 5-agent researcher pool is over-decomposed — all five "retrieve grounding evidence from corpus X", which is a tool concern, not an agent concern.
- (3) <1 day per agent for a non-technical PM in Days 8–14 is unrealistic for prompt quality.
- (4) The demo can credibly show 3–4 agents on screen in 3 minutes, not 10+, so the cost of 12 agents doesn't fully pay off in the pitch.
- (5) The Arize rubric explicitly rewards loop quality + tracing/MCP usage + design + impact — agent count is not a listed criterion.

A **lean composite alternative** was sketched in Session 3: 5 runtime agents (Coordinator, Researcher with multi-tool, Strategist+Drafter, Adversarial Reviewer) + 1 offline Learning Coordinator = 6 total. This would cut build risk in half while preserving every Arize-judging hook.

The PM made an informed call to **keep 12 agents** as the audacious strategic bet, with explicit revisit triggers baked into the decision.

## Decision

**Part B architecture stays at the 12-agent composite swarm + 2 meta-agents (14 total components) as specified in PRD §12.** Honest architectural component breakdown documented in [docs/architecture/2026-05-27-aegis-arch.md §3.1](../architecture/2026-05-27-aegis-arch.md): 10 LLM agents + 1 LLM-as-judge panel + 1 mostly-deterministic evaluator + 2 background meta-agents.

Topology: **Composite Pattern** combining 6 of Google's 8 ADK multi-agent patterns — Coordinator/Dispatcher, Parallel Fan-Out/Gather, Sequential Pipeline, Generator + Critic, Iterative Refinement, Human-in-the-Loop.

## Alternatives Considered

- **Lean composite (5 runtime + 1 offline = 6 total):** Coordinator + Researcher (multi-tool) + Strategist + Drafter + Adversarial Reviewer + Learning Coordinator. Cleaner demo, more time per agent for prompt depth, same Arize judging hooks (Phoenix MCP load-bearing in Researcher + Learning Coordinator, real multi-agent composite pattern). **Rejected by PM 2026-05-27** — the audacity is the bet; agent count is part of the differentiation thesis.
- **Single agent with rich tooling (Part A only, no Part B):** Lowest-risk path. Rejected: collapses to the safety-net Day 7 submission; forfeits the "first self-improving multi-agent organism" pitch; doesn't differentiate from the typical Arize-track submission.
- **20+ agent ultra-swarm:** More audacity. Rejected without explicit discussion — already pushing the build-time ceiling at 12.
- **Defer agent count to `agent-system-architecture` skill run with no commitment:** Rejected — PM wanted commitment for clarity in PRD, AGENTS.md, demo script, and build plan.

## Consequences

- ✓ Preserves the "12-agent swarm" pitch language and PRD §10 audacious thesis.
- ✓ Architecture aligns with Google's official ADK multi-agent patterns (Composite is pattern #8 in the official guide).
- ✓ The Insurer Intelligence Agent + Learning Coordinator both heavily exercise Phoenix MCP — load-bearing thesis is structurally true.
- ⚠ **Build-time risk is high.** Days 8–14 = 7 days to scaffold + prompt + test 9 additional agents (beyond the MVP single agent). At <1 day per agent for solo non-technical PM, prompt quality risks being shallow across the swarm. Mitigation: `google-agents-cli scaffold` accelerates structural work; `create-agent-prompt` skill produces role prompts before Day 8; Day 10 progress gate forces re-evaluation if <50% have credible prompts.
- ⚠ **Demo coherence risk.** 3 minutes to show 10+ agents is genuinely hard. PRD §16 demo script handles this by showing the swarm via animated architecture diagram only for ~25 seconds; the rest of the demo focuses on the learning loop + Phoenix UI. If the demo doesn't read clearly by Day 15, compress demo-visible subset to 3–4 of the 12 — keep all 10+ in repo, demo selectively.
- ⚠ **Pre-mortem Cause M (UX too dev-toolish)** and **assumption-map R6 (judges think 12 agents is overkill)** both flagged this risk. Both stand as "monitor + revisit"; neither was a blocker per PM decision.
- ⚠ **Coordination cost** — ADK `session.state` as shared blackboard works for this scale, but namespaced keys per agent must be enforced to prevent silent overwrites. See `docs/architecture/2026-05-27-aegis-arch.md` §5.1.

## Revisit triggers (CRITICAL — these are the safety nets on the audacious bet)

These are mirrored in [AGENTS.md → Build Discipline](../../AGENTS.md) and [decision-log.md 2026-05-27](../memory/decision-log.md):

1. **Day 10 progress gate.** If <50% of the 9 specialist agents (beyond the single MVP agent) have credible role prompts and pass basic integration tests by EOD Day 10, escalate to PM with options (compress to the lean 5-agent composite). Do not silently downscope.
2. **Assumption A5 (Learning Coordinator autonomy) fails.** If the Day 10 go/no-go test shows hit rate < 1-in-10 OR > 30% absurd-edit rate, the 12-agent thesis is hollow — reopen architecture entirely; likely demote Part B to "manual learning with human approval" + keep multi-agent runtime.
3. **Demo coherence test (Day 15).** If the demo script can't credibly walk through ≥3 specialist agents on screen without overwhelming viewers, compress the demo-visible subset to 3–4 of the 12. Keep all in repo; demo selectively.
4. **Build-time slippage.** If Day 14 milestone (9-agent swarm shippable) slips by >2 days, escalate per Code-Wall Escalation Protocol — do NOT silently downscope.

## References

- PRD §12 — current 12-agent topology
- [Google's developer guide to multi-agent patterns in ADK, Dec 2025](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/)
- Pre-mortem Session 2 (Cause M); Assumption Map A5 + R6 — both flagged this risk
- Session 3 decision in [docs/memory/decision-log.md](../memory/decision-log.md)
- Architecture spec — [docs/architecture/2026-05-27-aegis-arch.md](../architecture/2026-05-27-aegis-arch.md)
