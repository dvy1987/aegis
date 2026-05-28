
---

## 2026-05-28 - Session 15 Handoff (Antigravity)

### Done
- Re-architected the case generator pipeline to clearly separate "Factual/Structural Diversity" (handled by Orchestrator) from "Stylistic/Clinical Diversity" (handled by the Adversarial Diversifier).
- Modified the Flaw Injector (P4) to dynamically pull real-world insurer patterns directly from `denial_patterns.json` instead of relying on hard-coded static levers.
- Restored the Adversarial Diversifier as the `StylisticDiversifier` (P5) directly after the Flaw Injector.
- Bounded P5 with extremely strict rules: do not invent nonsensical medical scenarios (e.g., hip replacement for a 16-year-old), do not mutate or erase P4's injected legal/algorithmic flaws, and preserve `submission_timestamp`/`denial_timestamp` precisely.
- Fully integrated timestamp constraints (1-5 minute deltas for AI algorithmic denials) across schemas and models.
- Reconciled `plan_funding_type` requirements, ensuring State Mandate patterns only apply to "fully_insured" plans.

### Debated
- Clarified the misunderstanding surrounding the "Adversarial Diversifier". Initially characterized merely as a "stylistic" mutator, it was correctly identified by the PM as a "Clinical/Procedural" mutator that swaps drugs, alters history, and provides grounding metrics to prevent LLM mode-collapse.
- Assured the PM that placing P5 *after* P4 would not destroy the carefully crafted legal flaws by implementing strict preservation directives in the P5 prompt.

### Decisions
- Separate the roles of Orchestrator (factual spread), Flaw Injector (legal/algorithmic traps), and Stylistic Diversifier (clinical history/prose mutation) to achieve a robust 100-case dataset.
- Added `StylisticDiversification` to `models.py` and implemented `run_stylistic_diversifier` in `agents.py`.

### Deferred
- **Execute Generation Trial:** The trial (`uv run python -m app.case_generator.cli --count 12 --split test`) was queued but the session was closed before execution.
- **ClaudeVertexBackend Implementation:** Wiring Claude-on-Vertex as the critic backend (G1 task) is still pending.
- **T3.5 Demo Capture & T4.1 Live Trace Retrieval:** Still waiting to be executed.

### Next Agent Should Know
- The generation swarm now consists of 5 stages: P1 (Scenario), P2 (Drafter), P3 (Clinical), P4 (Flaw Injector), P5 (Stylistic Diversifier).
- The pipeline syntax has been verified (`uv run python -c "from app.case_generator import pipeline"`).
- The very next step should be running the generation trial to validate the dynamic flaw injection and stylistic diversification.

### Revisit Triggers
- If P5 is found to be altering legal flaws despite the prompt guardrails, we may need to enforce preservation deterministically outside the LLM or increase the critic weighting on flaw preservation.
- If the case generation discard rate spikes because of P5 mutations contradicting the P1 scenario, tune the temperature or prompt for P5.

### Working Tree
- New: `backend/app/case_generator/prompts/p5_stylistic_diversifier.txt`
- Modified: `backend/app/case_generator/models.py`, `backend/app/case_generator/agents.py`, `backend/app/case_generator/pipeline.py`, `backend/app/case_generator/prompts/p4_realistic_flaw_injector.txt`, `backend/app/case_generator/prompts/p1_scenario_planner.txt`, `eval/case_schema.json`.
