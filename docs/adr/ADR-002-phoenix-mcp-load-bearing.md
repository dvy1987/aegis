# ADR-002: Arize Phoenix Cloud + MCP as the load-bearing observability + introspection layer

**Date:** 2026-05-27 (synthesizing a Session 1 decision)
**Status:** Accepted (retrospective)
**Mode:** SYNTHESIS — decisions inferred from repo state as of 2026-05-27; not contemporaneous. The MCP-load-bearing framing is contemporaneous to Session 1 strategic positioning but was not previously written into an ADR.

## Context

Aegis is submitted to the Arize partner track of the Google Cloud Rapid Agent Hackathon. The track's judging rubric ([docs/challenge.md](../challenge.md)) has four co-equal sub-criteria + a bonus:
1. Technical implementation
2. **Meaningful use of tracing and MCP** ← co-equal pillar
3. **Quality of the self-improvement loop** ← co-equal pillar
4. Overall impact
5. Bonus: agents that use observability data to improve over time

The strategic thesis Aegis bets on is making the self-improvement loop **structurally dependent** on Arize Phoenix Cloud + the Phoenix MCP server — so that the demo can run a counterfactual where disabling Phoenix MCP visibly degrades agent quality. This isn't decorative observability; it's load-bearing infrastructure.

## Decision

**Use Arize Phoenix Cloud (free tier) as the system observability + eval surface, with the `@arizeai/phoenix-mcp` server configured as a runtime tool source on every ADK agent. Phoenix MCP is load-bearing — the Insurer Intelligence Agent and the Learning Coordinator both depend on it for their core function.**

Specifically:
- All ADK agent calls auto-instrumented via `openinference-instrumentation-google-adk` → traces sent to Phoenix Cloud. **As of 2026-06-07:** v1 (`aegis-v1-api`) → project **`default`**; swarm (`aegis-swarm-api`) → **`aegis-hackathon`**. Early T1.3 traces may remain in `aegis-hackathon` as archive; new v1 work uses `default`. See ADR-006 (amended) and decision-log §2026-06-07.
- Phoenix Datasets store benchmark splits (`benchmark_train_v1`, `benchmark_holdout_v1`, ...).
- Phoenix Prompts version every prompt; the Learning Coordinator bumps versions on promotion.
- Phoenix Experiments capture every v_n vs v_{n+1} comparison.
- Phoenix MCP server (`@arizeai/phoenix-mcp`, via npx) registered as ADK tool source. The Insurer Intelligence Agent queries `phoenix_trace_summary({insurer, denial_type, quality_score__lt, limit})` at runtime to read past failure patterns. The Learning Coordinator queries Phoenix MCP to identify failure clusters and propose patches.

## Alternatives Considered

- **Self-hosted Phoenix [INFERRED]:** Full control, no quota limits. Rejected: extra DevOps overhead for solo PM build; free Phoenix Cloud tier is sufficient at our scale (~200 runs × 14 agents × benchmark sizes). Revisit if Phoenix Cloud quotas approach 80% during build.
- **LangSmith [INFERRED]:** Strong tracing + eval product. Rejected: not the Arize partner — wrong submission track. Even if usable, picking LangSmith would forfeit the entire submission positioning.
- **Helicone / Logfire / OpenTelemetry-only [INFERRED]:** Generic OTel collection. Rejected: no MCP server, no eval/dataset/experiment primitives, no prompt versioning. Could not support the load-bearing self-improvement thesis.
- **Phoenix tracing without MCP [INFERRED]:** Use Phoenix only as a passive trace store; agent does not introspect at runtime. Rejected: the load-bearing thesis collapses; demo counterfactual ("disable Phoenix MCP → quality drops") loses its mechanism; the Arize bonus criterion (agents using their own observability data to improve) loses its strongest evidence.

## Consequences

- ✓ The Arize-track positioning thesis is architecturally true, not just marketing — disabling MCP genuinely degrades quality.
- ✓ All eval primitives (datasets, experiments, judges, prompts) live in one product; no integration glue.
- ✓ Free tier covers expected hackathon scale; cost ceiling estimated <$50 if upgrade needed.
- ✓ MCP server runs via `npx` in the agent runtime container — no separate deployment.
- ⚠ **Single point of failure for the demo.** If Phoenix Cloud has an outage during the demo recording window, the counterfactual beat fails. Mitigation: pre-record the counterfactual on a stable day; have backup screenshots ready.
- ⚠ **Free tier limits.** Estimated trace volume across Days 1–20 is high. Mitigation: monitor quota usage from Day 3; upgrade if approaching 80%.
- ⚠ **Phoenix MCP + ADK integration immaturity** — flagged as critical assumption A4 in [assumption-map.md](../research/assumption-map.md). Day 1–2 spike must verify latency < 5s and structured-output reliability. Open question [J1](../open-questions.md) — observability skill from `google-agents-cli` may conflict; sanity check needed.
- ⚠ **Vendor lock-in.** Switching observability post-hackathon would require re-instrumenting all agents and porting trace history. Acceptable for hackathon; revisit if Aegis becomes a long-term product.

## Revisit triggers

- Assumption A4 (Phoenix MCP + ADK integration maturity) fails on Day 2 — fall back to Phoenix SDK directly; lose some pitch shine; preserve the loop.
- Free tier quota exceeds 80% by Day 10 — upgrade to paid tier (≤$50 ceiling already approved).
- `google-agents-cli-observability` skill conflicts with Phoenix MCP setup — Skip the agents-cli observability skill, keep Phoenix as primary.

## References

- Hackathon brief — [docs/challenge.md](../challenge.md)
- Phoenix docs — https://docs.arize.com/phoenix
- Phoenix MCP guide — https://docs.arize.com/phoenix/integrations/mcp/phoenix-mcp-server
- Arize hackathon quickstart — https://github.com/Arize-ai/gemini-hackathon
- Assumption map A4 — [docs/research/assumption-map.md](../research/assumption-map.md)
