# ADR-001: Use Google ADK as the agent framework

**Date:** 2026-05-27 (synthesizing a Session 1 decision)
**Status:** Accepted (retrospective)
**Mode:** SYNTHESIS — decisions inferred from repo state as of 2026-05-27; not contemporaneous.

## Context

Heuristics is a hackathon submission for the Google Cloud Rapid Agent Hackathon — Arize partner track. The hackathon brief ([docs/challenge.md](../challenge.md)) explicitly requires a "code-owned agent runtime" for Arize-track submissions: Gemini CLI, Gemini Enterprise Agent Platform SDK, Google ADK, Agent Runtime, or Cloud Run. **The visual Agent Builder is not supported.** We need to instrument code directly with `openinference-instrumentation-google-adk` for the Phoenix-MCP-load-bearing thesis to work.

The system must support:
- Multi-tool single-agent execution (Part A — MVP)
- Multi-agent composite topology with Coordinator + Parallel + Sequential + Generator-Critic patterns (Part B)
- Native OpenInference auto-instrumentation
- Phoenix MCP server as a runtime tool source
- Cloud Run deployment

## Decision

Use **Google ADK** (Agent Development Kit, Python) as the agent framework for both Part A and Part B.

## Alternatives Considered

- **Raw `google-genai` SDK [INFERRED]:** Lower abstraction; full control of LLM calls. Rejected: the hackathon brief lists ADK as the recommended Arize-track runtime; `openinference-instrumentation-google-adk` is the most mature auto-instrumentor; building multi-agent orchestration from scratch on raw SDK would burn build time.
- **LangGraph [INFERRED]:** Strong multi-agent primitives; popular in the ecosystem. Rejected: not on the Arize-track approved runtime list per the hackathon brief; OpenInference support exists but ADK is the first-party path; switching frameworks late would invalidate `agents-cli` adoption (see [ADR-005](ADR-005-google-agents-cli-dev-workflow.md)).
- **CrewAI [INFERRED]:** Multi-agent-first design with role-based abstractions. Rejected: not on the Arize-track approved runtime list; weaker Cloud Run integration patterns; would force a different observability path than Phoenix-via-OpenInference-via-ADK.
- **Gemini Enterprise Agent Platform SDK [INFERRED]:** Higher-level, more enterprise-oriented. Rejected for solo PM build: more setup overhead than ADK; ADK is the open-source path and is documented as the substrate the Agent Platform builds on.

## Consequences

- ✓ Native compatibility with `openinference-instrumentation-google-adk` — Phoenix tracing works out of the box.
- ✓ Native compatibility with Phoenix MCP server as a tool source — load-bearing MCP claim is supported by first-party plumbing.
- ✓ Native compatibility with `google-agents-cli` (see [ADR-005](ADR-005-google-agents-cli-dev-workflow.md)) — scaffold/eval/deploy/observability all work with zero adaptation.
- ✓ First-party Google support; documentation maturing rapidly through 2025–2026; multi-agent patterns guide officially published Dec 2025.
- ⚠ **Vendor lock-in.** Switching frameworks post-hackathon would require porting all agents, tools, and instrumentation. Acceptable for a hackathon submission; revisit only if Heuristics becomes a longer-lived product.
- ⚠ ADK API is still maturing — minor version bumps may require code changes. Mitigation: pin the ADK version in `pyproject.toml`; bump deliberately.
- ⚠ Python-only — locks the backend to Python 3.11+. Acceptable.

## Revisit triggers

- If ADK introduces breaking changes that affect Phoenix instrumentation in our build window, freeze on the last-working version and re-evaluate.
- Post-hackathon: if Heuristics becomes a long-term product and a different framework offers materially better DX or features, plan a porting cycle.

## References

- Hackathon brief — [docs/challenge.md](../challenge.md)
- ADK docs — https://google.github.io/adk-docs/
- ADK multi-agent patterns guide (Dec 2025) — https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/
- OpenInference ADK instrumentor — https://github.com/Arize-ai/openinference
- ADK GitHub — https://github.com/google/adk-python
