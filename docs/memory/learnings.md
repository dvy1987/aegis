# Learnings

Known patterns and gotchas. Newest at the bottom. Each entry is dated and cites evidence.

---

## 2026-05-30 — Structural audit (Claude, via `/graphify`)

Findings from a full-repo knowledge-graph analysis. See
[orientation-map.md](orientation-map.md) for the complete synthesis and `graphify-out/` for the
queryable graph.

- **The submission thesis is unbuilt.** Part B's swarm runtime (`backend/app/aegis_swarm/agent.py`)
  is a 15-line stub, and there is no `learning_coordinator.py` / `pattern_synthesizer.py`. The
  self-improvement loop — the whole Arize-track pitch — exists only in docs.
- **`phoenix_mcp_lookup` is a stub** returning hardcoded `cold_start`/`disabled` values. The demo
  counterfactual ("disable Phoenix MCP → quality collapses") cannot be demonstrated until the live
  wiring (T4.1) is done. Treat the "load-bearing" claim as *aspirational until T4.1 lands*.
- **Gotcha — blueprint/reality layout drift.** The architecture spec (§9) describes
  `backend/src/agent/orchestrator.py`, `researchers/`, `learning/`, etc. The real code lives in
  `backend/app/{aegis_v1,aegis_swarm,case_generator,evals}`. Trust the code, not the spec's tree;
  the spec needs reconciling.
- **Gotcha — missing dirs.** `playbooks/` and `proposals/` (referenced throughout the architecture
  and HITL design) do not exist on disk. Any code assuming they're present will fail.
- **Same-model judging is the accepted reality.** The G1 plan for a different-family
  (Claude-on-Vertex) critic was dropped; Gemini judges Gemini. Lean on deterministic gates +
  κ≥0.6 calibration as the only bias mitigations.
- **Environment gotcha.** Some dev machines have **no GCP/Gemini/ADC**. On those, Vertex case
  generation, live judging, and agent runs cannot execute — only the offline-heuristic judge
  (`OfflineHeuristicJudgeClient`) and the deterministic v1 pipeline run locally. Check for ADC
  before assuming a cloud path works.
- **Onboarding shortcut.** A `/graphify` graph of the repo persists in `graphify-out/`. Use
  `/graphify query "<question>"` and `/graphify --update` instead of re-reading the corpus.
