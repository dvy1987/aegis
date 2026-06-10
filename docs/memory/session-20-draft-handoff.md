# Session 20 - Draft Handoff & Outstanding Tasks Backlog

This document tracks all deferred and outstanding tasks aggregated across Sessions 1–19. We will mark these as complete as we resolve them in Session 20.

## 1. High-Priority Code & Audit Fixes
- [x] **Stale File References:** Fix the ~9+ files referencing the deleted `fast_api_app.py`, port `8000`, and `app.agent`. Ensure `pytest tests/unit` passes.
- [x] **Phoenix Project Name Decision:** Keep `default` for v1 and `aegis-swarm` for swarm. No new projects.
- [x] **Simulator Threshold Logic:** Explicitly document the v1 simulator threshold (requires 10/10 to approve) as an intentional design choice for the demo arc.

## 2. Demo & Tracing
- [ ] **T3.5 Demo Capture:** Record the first run of the "weak-v1" agent. (MUST be done before any prompt improvements).
- [ ] **T4.1 Live Phoenix MCP Integration:** Wire the `phoenix_mcp_lookup` tool (currently a stub returning hardcoded data) to the live MCP server.
- [ ] **Arize Cloud Auth Resolution:** Fix trace retrieval auth or fall back to direct Phoenix SDK REST calls if `PHOENIX_CLIENT_HEADERS` fails.

## 3. Case Generation & Evaluators (Part A Benchmark)
- [ ] **Execute the Generation Trial:** Run `uv run python -m app.case_generator.cli --count 4 --split test` to generate benchmark cases using GCP ADC.
- [ ] **Validate Difficulty Distribution:** Verify the generated case difficulty targets (e.g., Easy, Medium, Hard).
- [ ] **Gemini/Cloud Calibration for Part A Judge Panel:** Run the seven Part A judge prompts against calibration examples using Gemini via GCP.
- [ ] **Phoenix Eval Metadata Integration:** Send evaluation metrics and metadata back into Phoenix traces.
- [ ] **Backfill Legacy Case Provenance:** Regenerate/backfill provenance for older cases with a `weak_teacher_packet`.

## 4. Frontend & Design (T1.3+)
- [ ] **T6.2 Workbench UI:** Build frontend case selector, v1/v3 toggle, side-by-side appeal, eval panel, simulator, Phoenix link-outs.
- [ ] **8 Bespoke SVGs:** Draw custom icons (denial, appeal, draft-letter, deadline, evidence, doctor, insurer, signature-dot variants).
- [ ] **Stylelint Enforcement:** Implement rules rejecting raw `lucide-react` imports outside of `src/icons/` and default Tailwind palette names.

## 5. Strategy & Remaining "Open Questions"
- [ ] **A3 Case Credibility (Day 3):** Outside reader test for synthetic cases.
- [ ] **J2 Deploy Tooling:** Determine if `agents-cli deploy` works for 2-service Cloud Run or write custom script.
- [ ] **T4.4 Playbooks & T2.3 Corpus:** Create actual playbook content and corpus content (currently empty/thin/defaults).
