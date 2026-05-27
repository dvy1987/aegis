# Design: Autonomy Ladder Mechanics & Thresholds
Date: 2026-05-27  |  Status: Approved

## Summary
Defines the concrete thresholds and mechanical privileges for the Learning Coordinator's 3-stage competency-gated autonomy ladder (Apprentice → Journeyman → Master).

## Problem
The PRD and README defined the concept of an autonomy ladder, but left the actual numerical thresholds as placeholders ("TBD"). We needed specific volume and quality triggers that balance real-world safety with the need to demonstrate the autonomous loop during a 100-case hackathon benchmark.

## Approach
**The Moderate Scale with an Aggressive Master Stage (Option B/C Hybrid).** 
We chose thresholds that are rigorous enough to be credible (requiring a 12.5% success rate on 200 iterations to reach Master), but we gave the Master stage maximum freedom (Option C) to create a compelling demo story of an AI that rewrites its own core instructions rapidly, bounded by a strict circuit breaker.

## Architecture & Thresholds

| Stage | Trigger to Enter | Privileges / Mechanics |
|---|---|---|
| 🟢 **Apprentice** | Default starting state | - Every proposed patch requires a PM approval click in the UI.<br>- Patches limited to playbook updates. |
| 🟡 **Journeyman** | **10** PM-approved proposals AND<br>Held-out composite score **≥ 0.60** | - Fully autonomous promotion.<br>- Hard gates: lift ≥ +3%, zero safety/hallucination regressions.<br>- Rate limit: 5 promotions/day.<br>- Patches limited to playbook updates. |
| 🔴 **Master** | **25** auto-promotions (while Journeyman) AND<br>Held-out composite score **≥ 0.75** | - Fully autonomous promotion.<br>- Relaxed quality gate: lift ≥ +1%.<br>- Raised rate limit: 20 promotions/day.<br>- **Broader patches:** Can rewrite Strategist agent system prompts, not just playbooks. |

## Key Decisions
**1. Master Stage Aggressiveness (Option C):** We explicitly decided to allow the Master stage to make high-frequency (20/day) micro-optimizations (+1%) and rewrite core agent instructions. This maximizes the learning rate but introduces the risk of reward hacking.

## Edge Cases & Safety Nets
**Reward Hacking (Overfitting):** Because the Master stage moves fast and changes deep rules, it might find ways to game the rubric without improving the letter. 
*Mitigation:* **The Auto-Demotion Circuit Breaker.** If the system's overall composite quality drops by >10% over any 10-run rolling window, it is instantly demoted back to Journeyman and stripped of prompt-rewriting privileges.

## Testing
- Unit tests to verify the counting logic (e.g., system accurately tracks consecutive auto-promotions).
- Integration test simulating a 10% quality drop to verify the auto-demotion circuit breaker fires.

## Non-Goals
- We are not allowing the Learning Coordinator to rewrite *all* agents' prompts (e.g., the Safety Judge or Orchestrator are strictly off-limits to prevent self-lobotomization). Prompt rewriting is limited to the drafting/strategy agents.

## Open Questions
*(None - thresholds are locked for build)*
