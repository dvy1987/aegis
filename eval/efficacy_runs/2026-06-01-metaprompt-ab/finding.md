# Reflection meta-prompt A/B — Finding

**Date:** 2026-06-01 · **Task held fixed:** reflect `drafter_v1` on `appeal_vector_capture`,
same laundered signal, same 4-case held-out slice as Run #1 (`test_case_01..04`).

We A/B'd the optimizer's OWN instruction (`build_reflection_prompt`) — comparing the
current `base` meta-prompt against a new `critique_plus` variant that forces an explicit
2-sentence single-flaw diagnosis then a MINIMAL edit (no new section unless it is the
smallest change that closes the gap).

## Result

| variant | held-out composite | lift vs v1 (0.73) | added body words | appeal_vector_capture mean | case_specific_clinical_rebuttal mean |
|---|---|---|---|---|---|
| **base** (= `drafter_v2`) | **0.88** | **+0.15 / +20.5%** | 129 | 5.0 | 5.0 |
| critique_plus | 0.835 | +0.105 / +14.4% | **40** | 4.5 | 4.5 |

**Quality winner: `base`** (Δ composite = +0.045). Both kept all hard gates PASS and
`grounding` at the corpus-bound 3.0.

## Interpretation (honest)
`critique_plus` did exactly what it was designed to do — a **3.2× tighter edit** (40 vs
129 added words). But on held-out cases that economy cost robustness: its single-lever
minimal instruction **under-captured** the appeal vector on one held-out case and the
case-specific clinical rebuttal on another (4.5/4.5 means vs base's 5.0/5.0). The fuller
`base` reflection — which converged on TWO explicit levers (confront the strongest stated
ground head-on **and** audit for missing procedural/appeal-rights disclosures) —
generalized more reliably to cases the reflection never saw.

This is a real, non-trivial result: on this optimizer task a more elaborate two-lever
reflection beat a minimal single-lever edit on held-out quality, despite 3× the diff size.
Token economy did not compensate for the generalization loss.

## Decision
**`base` remains the default meta-prompt** for future reflection rounds. `critique_plus`
is **not** promoted. The `variant` parameter ships (tested), so the variant can be
re-evaluated in Tier 1 on harder/live cases — where a minimal-edit framing may matter more
once `grounding` headroom (live corpus) makes the optimizer task less ceiling-bound.

## Caveats
- Small N (4 held-out), single optimizer task, Claude-drafts/Claude-judges (same family).
- Both candidates measured on the SAME slice with the SAME calibrated rubric; `base`'s
  numbers are the replay-locked Run #1 v2 result. The discriminating cross-model A/B
  (Gemini drafting + independent judge + κ≥0.6) belongs to Tier 1.

## Artifacts
- `base/candidate_prompt.md` (= drafter_v2) · `critique_plus/candidate_prompt.md` +
  `critique_plus/{drafts,judgments}/` (4 held-out each) · `score_ab.py` · `result.json`
- Code: `app/learning/reflection_client.py` `build_reflection_prompt(..., variant=...)` +
  test `tests/unit/learning/test_reflection_client.py::test_build_reflection_prompt_supports_named_variant`.
