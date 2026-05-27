---
status: Draft
constitution: docs/constitution.md@1
slug: aegis-part-b-swarm
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

## Needs Clarification
- [NEEDS CLARIFICATION: For FR-2, does the Learning Coordinator run on a scheduled CRON job, or is it triggered manually by a button in the UI for the sake of the hackathon demo?] (CL-1)

## Review Checklist
- [x] WHAT not HOW
- [x] Given/When/Then ACs
- [x] Edge cases included
- [x] Out of scope specific
