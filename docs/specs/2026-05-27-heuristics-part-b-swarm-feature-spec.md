---
status: Draft
constitution: docs/constitution.md@1
slug: heuristics-part-b-swarm
---

# Feature Spec: Part B (Full Plan) — 12-Agent Swarm & Auto-Learning

## Summary
Part B upgrades the backend to a 12-agent swarm orchestrated by a Learning Coordinator. The system autonomously tests prompt patches against a 100-case benchmark, promoting successful patches across a 3-stage autonomy ladder (Apprentice → Journeyman → Master) based on rigorous LLM judge evaluations.

## Problem
A single static-prompt agent cannot adapt to new insurer tactics or fix its own edge-case failures. Scaling to 100 cases requires specialized agents (e.g., Medical Necessity, Legal Researcher) and an autonomous system that learns from failures to continuously improve the baseline composite score.

## User Scenarios
- **US-1 (Autonomous Improvement):** The Learning Coordinator runs in the background over 200 iterations. It identifies low-scoring traces via Phoenix MCP, proposes a playbook patch, runs the holdout cases, and auto-promotes the patch if it passes the Journeyman/Master thresholds.
- **US-2 (Circuit Breaker):** If a bad patch causes the 10-run rolling average quality score to drop by >10%, the system automatically demotes from Master to Journeyman and rolls back the patch.

## Functional Requirements
- **FR-1:** The backend MUST support a 12-agent topology (Triage, Orchestrator, 5 Researchers, Strategist, Drafter, Adversarial Reviewer, Learning Coordinator, Pattern Synthesizer).
- **FR-2:** The Learning Coordinator MUST query Phoenix MCP to analyze failure traces.
- **FR-3:** The system MUST implement the 3-stage Autonomy Ladder thresholds (Apprentice, Journeyman, Master).
- **FR-4:** The system MUST evaluate against a 100-case benchmark (60 train, 40 holdout).
- **FR-5 (credit assignment):** Each agent's prompt MUST be an individually-loadable, versioned component (a prompt registry), and each run MUST emit a per-agent, firewall-safe trace signal (role + prompt_version + laundered output summary). A documented dimension->agent map MUST exist so learning feedback can target the responsible agent OR a corpus gap. (See ADR-007, plan Session 27.)
- **FR-6 (GCP corpus):** Researcher retrieval MUST go through a `CorpusStore` seam with a local backend (offline) and a Vertex AI Search + GCS backend (live). (ADR-007.)
- **FR-7 (trust-gated discovery):** When retrieval is thin, the system MAY run a Vertex grounded search restricted to a trust allow-list; discovered literature MUST pass sanitize (`secure-*`) -> trust-tier filter -> provenance capture before autonomous ingest into the corpus with a full audit log + one-click removal. Citations MUST still come only from the corpus (discovery feeds the corpus; the corpus stays the sole citation source). Discovery MUST be rate-limited and off by default.

## Build scope note (Session 27)
This plan builds the **runtime swarm** offline-first (full 10-agent topology), with the live ADK graph + Vertex/GCS backends credential-gated, and the **learning-feedback-to-the-right-agent seams** (FR-5) in place. FR-2/FR-3/FR-4 (autonomous Learning Coordinator re-point, autonomy ladder, 100-case benchmark) are a deferred follow-on. **Deliberately weak v1 baselines are authored for THREE target agents** (PRD 15.5) — `drafter`, `strategist`, `medical_necessity` — chosen because they own three distinct, non-overlapping quality dimensions totalling 0.75 of the weighted composite, so the demo lift is both large and cleanly attributable per agent. The weak set is a config dial (`registry.WEAK_V1_AGENTS`); non-weak agents still improve when the judges find their owned dimension is the bottleneck (one component re-pointed at a time). Safety is never weakened — only quality dimensions.

## Non-Functional Requirements
- **NFR-1:** The learning loop MUST NOT violate the safety hard gates (J1 Safety, J2 Hallucination). A failure here MUST veto the promotion.
- **NFR-2:** LLM judge calls MUST respect the $200 API budget ceiling.
- **NFR-3:** Master stage prompt-rewriting MUST be restricted to drafting/strategy agents to prevent core-system corruption.

## Acceptance Criteria
- **AC-FR-3.1 (Journeyman Promotion):** Given the system is in Apprentice mode, When 10 proposals are approved and composite score ≥ 0.60, Then the system unlocks Journeyman mode (autonomous playbook patching).
- **AC-FR-3.2 (Master Demotion):** Given the system is in Master mode, When the rolling composite score drops by >10%, Then the system instantly demotes to Journeyman and disables system prompt rewriting.

## Edge Cases
1. The 12-agent swarm hits the Google ADK context window limits during handoffs.
2. The Learning Coordinator enters an infinite loop, proposing the exact same patch repeatedly after rejection.
3. A patch improves "Persuasive Coherence" (J7) but subtly lowers "Evidence Completeness" (J5) — how is the trade-off handled if the composite increases?

## Out of Scope
- Training custom local models (we use Gemini 3).
- Fine-tuning the LLM weights (we only do in-context prompt/playbook patching).

## Constitution Waivers
- None.

## Resolved Clarifications
- **CL-1 (resolved Session 27):** For the hackathon demo the Learning Coordinator is **triggered manually** (a button in the demo UI), not a scheduled cron. A cron/scheduled trigger is out of scope for the demo. (The Coordinator re-point itself is a deferred follow-on; see Build scope note.)

## Review Checklist
- [x] WHAT not HOW
- [x] Given/When/Then ACs
- [x] Edge cases included
- [x] Out of scope specific
