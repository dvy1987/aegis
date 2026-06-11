# Credit-Assignment Map: quality dimension -> responsible swarm component

**Status:** Active (Session 27). Consumed by the Learning Coordinator re-point (plan Phase 6).

The Learning Coordinator scores each run on 5 weighted quality dimensions
(`backend/app/learning/models.py::DIMENSIONS`). In Part A there was one evolvable
component (the drafter prompt), so "fix the weakest dimension" trivially meant
"evolve the drafter". In the swarm there are 10 agents + the corpus, so a weak
dimension must be **routed to the component actually responsible for it** -
otherwise the coordinator evolves the wrong agent and learning is noise.

This document is that routing table. It maps each dimension to (a) the primary
responsible agent **prompt component** (a `registry` role / `component_id`) and
(b) whether a **corpus gap** is a plausible alternative cause (auto-served by
`LiteratureDiscovery`, ADR-007). Per-run attribution is supported by the
per-agent firewall-safe trace signal (plan Phase 3): each span records
`role + prompt_version + laundered output summary`.

## The map

| Dimension (weight) | Primary component (`component_id`) | Secondary | Corpus-gap plausible? | Why this owner |
|---|---|---|---|---|
| `grounding` (0.30) | `drafter` | responsible researcher; `strategist` | Yes - missing authority | Drafter must cite only strategy citations that trace to corpus; untraceable/invented citation is a drafter failure unless the needed authority is absent (corpus gap). |
| `appeal_vector_capture` (0.25) | `strategist` | `triage`, `insurer_intelligence` | Rarely | Strategist picks the archetype + lead angle (the "appeal vector"); wrong vector is a strategy failure. Bad routing (triage) or missing insurer tactic are secondary. |
| `case_specific_clinical_rebuttal` (0.20) | `medical_necessity` | `drafter` | Yes - clinical authority gap | The clinical rebuttal originates in the Medical Necessity brief; if the brief is thin because the clinical corpus lacks the authority, route to corpus gap, else to the researcher prompt. |
| `evidence_completeness` (0.15) | `strategist` (`evidence_checklist_for_drafter`) | researchers' `missing_evidence` | **Yes - primary alt cause** | Often a corpus gap: the right evidence/authority is not in the corpus. This is the dimension `LiteratureDiscovery` most directly improves. |
| `persuasive_coherence` (0.10) | `drafter` | `adversarial_reviewer` | No | Prose coherence is the drafter's job; the adversarial reviewer is the safety net that should have caught it. |

Dimension weights are mirrored from `DIMENSION_WEIGHTS`.

## Resolution algorithm (Phase 6 consumes this)

1. Read held-out scored runs from Phoenix (laundered; `ScoredRun`).
2. Compute per-dimension means; pick the **weakest weighted dimension**.
3. Look up its **primary component** in the map above.
4. **Corpus-gap check** (only for dimensions flagged corpus-gap-plausible):
   if failing runs' briefs carry `evidence_gaps` / `missing_evidence` AND the
   responsible researcher's `status` was `partial`/`empty`, the cause is a
   corpus gap -> queue a `LiteratureDiscovery` ingest target instead of (or in
   addition to) evolving the prompt.
5. Otherwise resolve to the primary component's prompt and hand it to the
   `SwarmExperimentRunner` (swap that one agent's prompt via the registry,
   re-score via `run_evaluated_swarm_case`, measure held-out lift).
6. Promotion still requires the safety gates + human approval (Part B autonomy
   is deferred; see PRD 15.2 and the Build scope note in the feature spec).

## Weak-v1 demo scaffold (Phase 3) — which agents start weak

Three agents ship on a deliberately weak baseline (`registry.WEAK_V1_AGENTS`,
`<role>_v1_weak.md`) so the self-improvement loop has visible, attributable
headroom. They were chosen to own **three distinct, non-overlapping dimensions**
(no confounding) covering **0.75 of the weighted composite**:

| Weak agent | Owned dimension(s) | Weight |
|---|---|---|
| `drafter` | `grounding` + `persuasive_coherence` | 0.40 |
| `strategist` | `appeal_vector_capture` + `evidence_completeness` | 0.40 |
| `medical_necessity` | `case_specific_clinical_rebuttal` | 0.20 |

`insurer_intelligence` is kept strong (its degradation story is the Phoenix-MCP-off
counterfactual, not a weak prompt); `adversarial_reviewer` is kept strong at
**baseline** (never weaken a safety gate) but remains **evolvable** when the credit
map routes a fix there under HITL/Apprentice. The weak set is a **dial** — every
other pipeline agent (`triage`, `legal_researcher`, `policy_detective`, etc.) is
re-pointed when the judges + trace signals attribute the bottleneck to that role
(see `learning/credit_resolution.py`, Phase 6). The
strong reference prompt lives in `prompts/targets/<role>.md` as a **human evaluation
ceiling only** (`registry.load_target_reference`) — it is NOT a loadable version and
NEVER an optimizer input (see Invariants). **Safety is never weakened — only quality.**

## Per-agent trace signal (Phase 3) — the attribution input

Each run emits one `AgentTraceSignal` per invoked agent (in
`SwarmRunArtifacts.agent_trace_signals`), built by `tools.make_agent_trace_signal`:
`role + prompt_version + is_weak_v1 + owned_dimensions + status +
finding/citation counts + risk_flags + a templated summary`. It is **firewall-safe**
(INV-2): summaries are structural one-liners (enums + counts) — never raw letter
text, brief quotes, agent `thinking`, PHI, or answer-key provenance. This is the
laundered signal Phase 6's resolution algorithm joins with the dimension scores to
route a fix to the responsible agent. Live wiring to Phoenix spans is Phase 4.

## Invariants

- **One component at a time.** A re-point evolves exactly one prompt component
  (or queues one corpus-gap target), so lift is attributable.
- **Firewall preserved.** Attribution uses only laundered trace signals - never
  answer-key provenance (INV-2). The map keys off dimension scores + laundered
  notes, not benchmark labels.
- **Map is versioned with the topology.** If an agent's responsibility changes,
  update this table in the same change.
- **No known-good leakage (evolution integrity).** The optimizer seeds ONLY from
  `registry.current_version` (the weak baseline) and evolves using laundered judge
  feedback alone. The strong reference prompts in `prompts/targets/` are a **human
  evaluation ceiling, NEVER an optimizer input** - they are not loadable as a
  registry version, so a seeding step cannot read them. Success is **held-out
  composite lift vs the weak baseline**, never similarity to the strong target.
  (Distinct from the firewall: that blocks benchmark answer-key labels; this blocks
  a known-good prompt. Both must hold.) See `prompts/WEAK_BASELINES.md`.
- **No experiment metadata in runtime prompts.** A `v1_weak` prompt body never tells
  the model it is "deliberately weak" - that would bias generation. Rationale lives
  in `WEAK_BASELINES.md`, which is never loaded into agent context.

## References
- `backend/app/learning/models.py` (DIMENSIONS, DIMENSION_WEIGHTS, ScoredRun, DimensionSignal)
- `backend/app/aegis_swarm/prompts/registry.py` (component_ids = agent roles)
- ADR-007 (corpus as a second learning surface) - [ADR-007](../adr/ADR-007-gcp-corpus-vertex-discovery.md)
- Architecture spec section 5.5 (anti-cheating firewall) - [arch](2026-05-27-heuristics-arch.md)
