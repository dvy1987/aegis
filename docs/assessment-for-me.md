# Arize Track — Hackathon Requirements Assessment

**Date:** 2026-06-07  
**Scope:** General challenge requirements + Arize partner track specifics.  
**Explicitly excluded from this assessment:** whether v1 product flows run through the ADK agent reasoning loop (documented separately in [plans/2026-06-07-aegis-v1-adk-migration-plan.md](plans/2026-06-07-aegis-v1-adk-migration-plan.md)).

---

## Summary

| Area | Verdict |
|---|---|
| Gemini 3 as the brain | **Met** |
| Partner MCP (meaningful, runtime) | **Strong** |
| Move beyond chat / multi-step / human oversight | **Met** |
| OpenInference + Phoenix Cloud tracing | **Partial** |
| Phoenix MCP runtime self-introspection | **Strong** |
| Evaluations on traces (LLM-as-judge) | **Strong** |
| Self-improvement from observability (bonus) | **Strong** |
| Code-owned runtime (Cloud Run) | **Met** |
| Hosted project URL | **Met** |
| Public repo + detectable license | **Met** (verify GitHub About shows Apache-2.0) |
| README accuracy for judges | **Stale** |

**Bottom line:** The Arize-track technical story (MCP, evals, self-improvement) is strong. Submission gaps are mostly operational (README freshness, live deploy env for citations). Tracing richness for LLM calls is thinner than it appears because raw `google.genai` calls are not auto-instrumented today.

---

## General challenge requirements

### Real-world problem + agent that accomplishes tasks (not just chat)

**Met.** Heuristics drafts US commercial health-insurance appeal letters from denial text — a concrete real-world problem. The student pipeline uses six tools in fixed order (`case_parser`, `corpus_retrieval`, `phoenix_mcp_lookup`, `playbook_loader`, `drafter`, `self_check`) plus an Outcome Simulator and a 7-judge eval panel. Product endpoints: `/v1/appeal` (live drafting) and `/v1/showcase` (self-improvement demo).

### Multi-step mission with human oversight

**Met.** The showcase runs a multi-stage learning loop (pre-measure → training signal → GEPA optimize → PM approval → promote → post-measure → rollback available). Human approval is required for promotion in Part A (Apprentice mode).

### Partner MCP integration

**Met (Arize).** See Arize track section below.

### Google Cloud Agent Builder

**Met for the Arize track.** The general challenge mentions Agent Builder; the **Arize track explicitly requires a code-owned runtime** (Gemini CLI, ADK, Agent Runtime, or Cloud Run) and states the visual Agent Builder alone is not supported for tracing. This project uses Cloud Run + instrumented Python — correct for the chosen track.

### Gemini 3

**Met.** Drafter, simulator, judges, and reflection default to `gemini-3.1-pro-preview` with `gemini-3.5-flash` fallback via [backend/app/gemini_retry.py](../backend/app/gemini_retry.py).

---

## Arize track requirements

### Code-owned agent runtime

**Met.** Backend and frontend deployed on Google Cloud Run:
- Backend: `https://aegis-v1-api-v6a3eydpoq-uc.a.run.app`
- Frontend: `https://aegis-frontend-v6a3eydpoq-uc.a.run.app`

Deploy scripts: [backend/deploy-v1.sh](../backend/deploy-v1.sh), [frontend/deploy.sh](../frontend/deploy.sh).

### Instrument with OpenInference

**Partial.** [backend/app/app_utils/telemetry.py](../backend/app/app_utils/telemetry.py) calls `phoenix.otel.register(auto_instrument=True)`. Installed instrumentor: `openinference-instrumentation-google-adk` ([backend/pyproject.toml](../backend/pyproject.toml)). **Not installed:** `openinference-instrumentation-google-genai`.

**Why this matters:** The live product flows (drafter, simulator, judges, reflector) call `google.genai` directly, not through the ADK Runner. The ADK instrumentor does not trace those raw calls. What reaches Phoenix today is primarily:
- App-level spans from `OtelPhoenixRecorder` (metadata + annotations, not full LLM prompts)
- ADK playground / any path that actually runs through ADK

See [assessment note: tracing richness](#tracing-richness) below.

### Send traces to Phoenix Cloud

**Met.** `PHOENIX_COLLECTOR_ENDPOINT` and `PHOENIX_API_KEY` (Secret Manager) configured in deploy. v1 pins `PHOENIX_PROJECT_NAME=default` in [backend/app/main_v1.py](../backend/app/main_v1.py).

### Configure Phoenix MCP for runtime introspection

**Strong.** [backend/app/aegis_v1/phoenix_mcp.py](../backend/app/aegis_v1/phoenix_mcp.py) launches `@arizeai/phoenix-mcp` via `npx`, calls `get-spans` and `get-span-annotations`, filters by insurer/denial_type slice, and returns laundered signal to `phoenix_mcp_lookup` in [backend/app/aegis_v1/tools.py](../backend/app/aegis_v1/tools.py). MCP-first with REST fallback. Counterfactual toggle: `PHOENIX_MCP_ENABLED=false` for demo contrast.

### Run evaluations on traces (LLM-as-judge / code evals)

**Strong.** [backend/app/evals/part_a/panel.py](../backend/app/evals/part_a/panel.py): 6 weighted LLM judges + 2 deterministic gates (safety, citation). Annotations written back to Phoenix spans via [backend/app/evals/part_a/recorder.py](../backend/app/evals/part_a/recorder.py) (`aegis_part_a_panel`).

### Bonus: self-improvement from observability data

**Strong.** Learning loop: Phoenix annotations → `LivePhoenixLearningStore` → `LearningCoordinator` / GEPA → `GeminiReflectionClient` proposes prompt/playbook changes → scored on holdout → human-approved promotion. Showcase UI demonstrates before/after with rollback.

---

## Submission checklist (Devpost)

| Item | Status |
|---|---|
| Hosted project URL | **Done** (frontend + backend Cloud Run URLs above) |
| Public GitHub repo + Apache-2.0 visible in About | **Verify** — [LICENSE](../LICENSE) exists at repo root |

---

## Gaps and risks (prioritized)

### P0 — submission blockers

1. **Demo video not recorded.** Required for Devpost.
2. **README stale.** [README.md](../README.md) Status still says "No code yet" and marks `eval/`, `playbooks/` as TBD. Misleading for judges.

### P1 — demo credibility

3. **`citations_used: 0` on live deploy.** If `VERTEX_SEARCH_*` env vars are not set on Cloud Run, judges hard-gate and composite scores collapse. Verify library env before recording demo. See [docs/memory/current-state.md](memory/current-state.md).

4. **Tracing richness.** Judges evaluate "meaningful use of tracing." Auto-traced LLM spans are thin because raw genai isn't instrumented. Options: full ADK migration (see plan doc) or add `openinference-instrumentation-google-genai` (lighter touch). Either path: decide Phoenix content-capture policy — denial text is in prompts; enabling full capture on `/appeal` risks PHI in Phoenix.

### P2 — polish

5. **Live credentialed rehearsal** of quick showcase run through approve still pending per current-state.

---

## Tracing richness

### Current state

- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` defaults to `"true"` in telemetry setup.
- Only the ADK OpenInference instrumentor is installed.
- Product LLM calls use raw `google.genai` → **not auto-traced** by the ADK instrumentor.
- `OtelPhoenixRecorder` writes tagged metadata spans + laundered judge annotations — valuable for the learning loop, but not full LLM call traces.

### Would switching to ADK completely fix this?

**Mostly yes, with caveats.**

If all v1 LLM calls (drafter, simulator, judges, reflector) run through ADK `LlmAgent`s invoked via ADK `Runner`, the installed `openinference-instrumentation-google-adk` would trace those calls — richer spans (model, tokens, tool steps where applicable) would appear in Phoenix.

**Caveats:**

1. **You must actually run through Runner**, not just define agents. Today `root_agent` exists but `/appeal` and `/showcase` bypass it.
2. **Deterministic Python** (gates, scoring, case_parser regex logic) won't get LLM-style spans unless wrapped as ADK workflow steps/tools.
3. **Content capture:** ADK tracing + `CAPTURE_MESSAGE_CONTENT=true` will export denial-letter text in prompts to Phoenix. For `/appeal` (possible real PHI), disable capture or redact before the ADK migration ships to production.
4. **Lighter alternative:** Adding `openinference-instrumentation-google-genai` instruments the current raw-genai path without a full ADK rewrite — also fixes tracing richness, same PHI caveat.

Recommended path for the hackathon narrative: **hybrid ADK migration** ([plans/2026-06-07-aegis-v1-adk-migration-plan.md](plans/2026-06-07-aegis-v1-adk-migration-plan.md)) — satisfies "built on ADK" and tracing richness together, with content capture turned off for safety.

---

## Evidence map (key files)

| Claim | File |
|---|---|
| Phoenix MCP runtime | [backend/app/aegis_v1/phoenix_mcp.py](../backend/app/aegis_v1/phoenix_mcp.py) |
| MCP tool in student pipeline | [backend/app/aegis_v1/tools.py](../backend/app/aegis_v1/tools.py) `phoenix_mcp_lookup` |
| Telemetry / OpenInference | [backend/app/app_utils/telemetry.py](../backend/app/app_utils/telemetry.py) |
| Judge panel | [backend/app/evals/part_a/panel.py](../backend/app/evals/part_a/panel.py) |
| Span annotations | [backend/app/evals/part_a/recorder.py](../backend/app/evals/part_a/recorder.py) |
| Self-improvement loop | [backend/app/learning/coordinator.py](../backend/app/learning/coordinator.py), [backend/app/aegis_v1/showcase_runner.py](../backend/app/aegis_v1/showcase_runner.py) |
| Raw genai clients (not ADK-traced today) | [backend/app/aegis_v1/drafter_client.py](../backend/app/aegis_v1/drafter_client.py), [backend/app/aegis_v1/simulator_client.py](../backend/app/aegis_v1/simulator_client.py), [backend/app/evals/part_a/llm_judges.py](../backend/app/evals/part_a/llm_judges.py) |
| ADK migration plan | [docs/plans/2026-06-07-aegis-v1-adk-migration-plan.md](plans/2026-06-07-aegis-v1-adk-migration-plan.md) |

---

## Related docs

- [docs/challenge.md](challenge.md) — hackathon brief
- [docs/memory/current-state.md](memory/current-state.md) — live project status
- [docs/demo-cheatsheet-pm.md](demo-cheatsheet-pm.md) — demo flow + Phoenix project names
- [docs/adr/ADR-002-phoenix-mcp-load-bearing.md](adr/ADR-002-phoenix-mcp-load-bearing.md) — why Phoenix MCP is structural

---

## Appendix A — Full requirement-by-requirement audit (2026-06-07 session)

Source: PM pasted the full Devpost / Arize track brief and asked for a thorough check against the current project (excluding the ADK runtime gap, which is documented in the migration plan).

### Judging criteria mapping

| Criterion | Assessment |
|---|---|
| **Technological implementation** | Strong on MCP + eval loop + Cloud Run; weakened by thin auto-tracing of live LLM calls and possible `citations_used: 0` on deploy without Vertex Search env. |
| **Design** | Frontend exists (`/appeal`, `/showcase`) with enterprise-trust UX intent per design brief; not formally re-audited in this pass. |
| **Potential impact** | Strong narrative (insurance denial asymmetry, KFF stats in README); synthetic cases only, no PHI in benchmark. |
| **Quality of the idea** | Self-improving agent via Phoenix MCP introspection is differentiated vs bolt-on tracing. |
| **Self-improvement loop (Arize-specific)** | Strong — GEPA + human approval + rollback + autonomy ladder designed. |

### General challenge — "What to Build"

| Requirement | Met? | Evidence |
|---|---|---|
| Functional agent powered by Gemini | Yes | All LLM clients use Vertex `google.genai` + Gemini 3.x models |
| Integrates Partner MCP server | Yes (Arize) | `@arizeai/phoenix-mcp` at runtime in `phoenix_mcp.py` |
| Solves a real challenge | Yes | US commercial appeal-letter drafting from denial text |
| Move beyond chat — uses tools | Yes | 6-tool student pipeline + simulator + judge panel + learning coordinator |
| Multi-step mission, human in control | Yes | Showcase stages + `needs_approval` + rollback |
| Google Cloud Agent Builder | Yes for Arize track | Code-owned Cloud Run runtime (visual Builder alone explicitly disallowed on Arize track) |

### Arize track — guideline checklist

| Arize guideline | Met? | Notes |
|---|---|---|
| Code-owned runtime (ADK / Cloud Run / etc.) | Yes | Cloud Run `aegis-v1-api` + `aegis-frontend` |
| Instrument with OpenInference | Partial | ADK instrumentor installed; raw genai calls not covered |
| Auto-instrumentors for ADK, GenAI, etc. | Partial | Only `openinference-instrumentation-google-adk` in `pyproject.toml` |
| Send traces to Phoenix Cloud | Yes | `phoenix.otel.register()` + collector endpoint + API key secret |
| Phoenix MCP configured for runtime introspection | Yes | MCP-first `fetch_slice_traces` → `phoenix_mcp_lookup` tool |
| Evaluations on traces (LLM-as-judge / code) | Yes | 6 LLM judges + 2 deterministic gates; annotations on spans |
| Bonus: improve from observability data | Yes | Learning loop reads laundered Phoenix annotations |

### What to Submit (Devpost)

| Item | Status |
|---|---|
| URL to hosted project | Done — see Cloud Run URLs in main doc |
| URL to public open-source repo | Verify repo is public on GitHub |
| Complete open-source license detectable in About | `LICENSE` is Apache-2.0 at repo root |
| ~3 minute demo video | Not done |
| Select track (Arize) | Manual on Devpost |
| Completed Devpost form | Manual |

---

## Appendix B — What's solidly satisfied (detail)

### Partner MCP — the centerpiece

This is real, not cosmetic. `phoenix_mcp.py` launches `@arizeai/phoenix-mcp` over stdio (`npx -y @arizeai/phoenix-mcp`), calls the `get-spans` and `get-span-annotations` MCP tools, filters to the case's insurer/denial_type slice, and feeds laundered signal back into drafting via `phoenix_mcp_lookup`. This matches the track requirement: *"query its own traces, prompts, datasets, and experiments as tools at runtime."* MCP-first with REST fallback. Counterfactual toggle `PHOENIX_MCP_ENABLED=false` supports the demo narrative (quality collapses without MCP memory).

### LLM-as-judge evals

`panel.py` runs 6 weighted LLM judges plus deterministic safety and citation gates. Annotations are written back onto Phoenix spans via `OtelPhoenixRecorder.annotate` → `log_span_annotations_dataframe` with name `aegis_part_a_panel`. Directly satisfies *"run evaluations on your traces."*

### Self-improvement loop (bonus criterion)

`GeminiReflectionClient` / `LearningCoordinator` consume laundered Phoenix annotations and propose new prompts/playbooks, scored as Phoenix experiments, promoted under human approval with rollback. This is the headline *"uses its own observability data to improve over time."*

### Gemini + Cloud Run + Phoenix Cloud

- Gemini 3: `gemini-3.1-pro-preview` default across drafter, simulator, judges, reflection; `gemini-3.5-flash` fallback in `gemini_retry.py`.
- Cloud Run: backend + frontend deployed (URLs in main doc).
- Phoenix: telemetry exports via collector; API key in Secret Manager; v1 project pinned to `default`.

### License

`LICENSE` at repo root is Apache 2.0. GitHub auto-detects this for the About section — confirm the repo is public before submission.

---

## Appendix C — Denial-letter text and Phoenix (PHI / content capture)

Investigated separately in the same session: does denial-letter text appear in Phoenix for `/appeal` or `/showcase` holdout cases?

### Chain of exposure (if instrumented)

1. `case_parser` stores full raw letter in `parsed_case.denial_text` and `clinical_context` (`tools.py` ~L181-182).
2. Drafter embeds entire `parsed_case` in Gemini prompt via `_build_contents` (`drafter_client.py`).
3. Simulator embeds `denial_text` and `clinical_context` directly in prompt (`simulator_client.py` ~L64-68).
4. `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` defaults to `"true"` (`telemetry.py`).

### Current verdict: NOT in Phoenix today

Prompt content is **not** exported because:
- Only `openinference-instrumentation-google-adk` is installed (not `google-genai`).
- Product flows use raw `google.genai`, which the ADK instrumentor does not trace.
- `OtelPhoenixRecorder` writes metadata + laundered scores only — never denial text.

### Latent risk

If `openinference-instrumentation-google-genai` is added, OR if flows migrate to ADK Runner with content capture still on, denial-letter text **will** appear in Phoenix prompts. Showcase holdout = synthetic (safe). `/appeal` product path = possible real PHI. **Decision required before enabling richer tracing on the live product path.**

---

## Appendix D — ADK gap (context for tracing; full plan elsewhere)

**Not scored in the main summary table** (PM asked to assess apart from ADK), but relevant to tracing and hackathon framing:

Today ADK is used as:
1. FastAPI web framework (`get_fast_api_app` in `main_v1.py`)
2. A registered `root_agent` reachable via ADK playground — **not invoked by `/appeal` or `/showcase`**

All real LLM intelligence runs through hand-written Python calling `google.genai` directly:
- Drafter, simulator, 6 judges, reflector
- `LiveExperimentRunner` is a custom Python class, not ADK `Runner`

Likely historical cause: `root_agent` sets both `output_schema` and `tools`, which ADK disallows on one `LlmAgent` — model-driven tool calling was unreliable, so `run_aegis_v1_pipeline` became the product path.

Migration plan (PM-approved hybrid, full v1 scope): [plans/2026-06-07-aegis-v1-adk-migration-plan.md](plans/2026-06-07-aegis-v1-adk-migration-plan.md). Implementation deferred.

---

## Appendix E — ADK migration vs tracing richness (Q&A)

**Question (PM):** Would switching to ADK completely fix the tracing richness issue?

**Answer: Mostly yes — but only if LLM calls actually run through ADK Runner, not just if you define ADK agents.**

### Why tracing is thin today

- `openinference-instrumentation-google-adk` is installed.
- Live flows (drafter, simulator, judges, reflector) call `google.genai` directly.
- The ADK instrumentor does not see those calls → no rich LLM spans in Phoenix.
- What you do get: app-level `OtelPhoenixRecorder` metadata spans + judge annotations (valuable for the learning loop, but not full LLM call traces).

### What full ADK migration fixes

If each LLM step becomes an `LlmAgent` invoked via `Runner` (per the hybrid migration plan), the ADK instrumentor traces them: model name, tokens, agent/tool structure in Phoenix. That fixes the richness gap for those calls.

### Caveats (all four matter)

1. **Defining agents is not enough.** `root_agent` already exists but `/appeal` and `/showcase` never invoke it. Fix = route real traffic through `Runner`.
2. **Not everything becomes an LLM span.** Deterministic Python (`case_parser` regex, `score_outcome`, safety gates) only appears as ADK workflow/tool steps if wrapped as ADK steps. Acceptable — judges care about LLM trace richness.
3. **PHI / content capture flips on.** ADK tracing + `CAPTURE_MESSAGE_CONTENT=true` exports denial-letter text in prompts to Phoenix. For `/appeal`, disable capture or gate it as part of migration.
4. **Lighter alternative.** Add `openinference-instrumentation-google-genai` without full ADK rewrite — also instruments current raw-genai path. Same PHI caveat.

### Recommendation for hackathon

| Path | Fixes tracing? | Fixes "built on ADK"? | Effort |
|---|---|---|---|
| Add `google-genai` instrumentor only | Yes (raw genai calls) | No | Low |
| Full hybrid ADK migration | Yes (via ADK instrumentor) | Yes | High |
| Status quo | No | No | — |

**Recommended narrative:** hybrid ADK migration — satisfies both "built on ADK" and tracing richness, with content capture turned off for `/appeal` safety.

---

## Appendix F — Net assessment for submission planning

### Ready to claim on Devpost / demo

- Gemini-powered multi-tool agent solving a real problem
- Meaningful Arize Phoenix MCP runtime integration (load-bearing, demo toggle)
- LLM-as-judge evals on traces
- Self-improvement loop using observability data
- Hosted on Cloud Run with Apache-2.0 license

### Must fix before submit

1. Record ~3-minute demo video
2. Update README (still says "No code yet")
3. Verify Vertex Search env on Cloud Run so citations and judge scores work live
4. Confirm GitHub repo public + license visible in About

### Should fix for judge confidence

5. Tracing richness (ADK migration OR `google-genai` instrumentor + content-capture policy)
6. Live credentialed rehearsal of showcase quick run through approve

### Explicitly out of scope for this assessment

- Swarm / Part B (`aegis-swarm` Phoenix project)
- Formal design-review score
- ADK implementation (plan written, not executed)
