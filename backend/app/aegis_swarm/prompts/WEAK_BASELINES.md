# Weak-v1 demo scaffold — design rationale (NOT a runtime prompt)

This document explains the deliberately-weak baselines (PRD §15.5). It is **never
loaded into any agent's context** — it does not match the `<role>_v*.md` version
glob, so the registry will not enumerate or send it to a model. Keeping this
rationale out of the prompt bodies is deliberate: an agent must not be told "you
are weak on dimension X" at runtime, or it may over-compensate (collapsing the
demo headroom) or under-perform (priming) — either way an uncontrolled confound.

## Which agents start weak, and on which dimension

`registry.WEAK_V1_AGENTS` pins these three to `<role>_v1_weak.md`. They were chosen
to own three **distinct, non-overlapping** quality dimensions totalling **0.75 of
the weighted composite**, so the self-improvement lift is both large and cleanly
attributable per agent:

| Weak agent | Owned dimension(s) | Weight | How its `v1_weak` is under-specified |
|---|---|---|---|
| `drafter` | `grounding` + `persuasive_coherence` | 0.40 | Loose citation discipline; no archetype-specific structure; no length/tightness discipline. |
| `strategist` | `appeal_vector_capture` + `evidence_completeness` | 0.40 | No deliberate archetype selection; generic lead angle; thin/optional evidence checklist. |
| `medical_necessity` | `case_specific_clinical_rebuttal` | 0.20 | General clinical support, not tied to the case's specific facts; optional missing-evidence enumeration. |

The weakness is expressed only as **under-specified instructions** in the prompt
body — never as self-aware meta-commentary about being weak.

## Kept strong (deliberately not weakened)

- `insurer_intelligence` — its degradation story is the **Phoenix-MCP-off
  counterfactual** (toggle MCP → empty brief → letter degrades), not a weak prompt.
- `adversarial_reviewer` — it is a **safety gate**; never weaken a guardrail.

## Safety invariant

The deliberate weakness is **quality-only**. Every `v1_weak` prompt keeps its full
safety guardrails (mandatory disclaimer, no-invention/no-fabricated-authority,
no-PHI, no "will win", no exclamation marks, "person" not "human"). We create
quality headroom, never safety headroom.

## Evolution-integrity invariant (read before building Phase 6)

- The Learning Coordinator/optimizer **seeds only from `registry.current_version`**
  (the `v1_weak` baseline) and generates fresh versions (`v2`, `v3`, …) from the
  weak baseline **plus laundered judge feedback ONLY**.
- The strong reference prompts live in `prompts/targets/<role>.md`. They are a
  **human evaluation ceiling** (e.g. "the loop recovered N% of the gap to our
  hand-written reference") and are **NEVER an optimizer input**. They are not
  loadable as a registry version (`available_versions` will not list them), so a
  seeding step cannot accidentally read them.
- Success is measured as **held-out composite lift vs the weak baseline**, never as
  similarity/distance to the strong target. Climbing "toward" the known-good prompt
  is not the metric; independently discovered lift is.

The weak set is a **dial** — edit `registry.WEAK_V1_AGENTS` (and drop a matching
`<role>_v1_weak.md`) to change how many agents start weak. Non-weak agents still
improve when the judges find their owned dimension is the bottleneck (one component
re-pointed at a time). See `docs/architecture/credit-assignment-map.md`.
