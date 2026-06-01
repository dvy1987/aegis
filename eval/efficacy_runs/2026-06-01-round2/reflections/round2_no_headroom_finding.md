# Round 2 — Finding: offline ceiling reached (no promotion)

**Date:** 2026-06-01 · **Baseline:** `drafter_v2` (promoted in Run #1) · **Split:** full 11-case train (`case_*`)

## What we did
Round 2 of the assistant-orchestrated manual GEPA loop. The Claude session played
drafter (11 fresh, firewall-isolated subagents — student packet + `drafter_v2.md` +
the fixed safety harness only) and the calibrated judge panel (11 subagents — letter
+ teacher packet + the Run-#1 calibrated rubric, 1/3/5 anchors, anchor 5 reserved).
We scored `drafter_v2` on the **full 11-case train split** (2.75× Run #1's 4 train
cases) to pick the next weakest *promptable* dimension.

## Result — no promptable offline headroom
Per-dimension mean anchor (v2, 11 train cases):

| dimension | mean | note |
|---|---|---|
| grounding | 3.0 | corpus-bound — no retrieved citations offline; a prompt edit cannot move it |
| appeal_vector_capture | 5.0 | at ceiling |
| case_specific_clinical_rebuttal | 5.0 | at ceiling |
| evidence_completeness | 5.0 | at ceiling |
| persuasive_coherence | 4.82 | weakest *promptable* — one case dinged for mild padding/repetition, otherwise 5 |

Train composite **0.876**; all 11 hard gates PASS.

**Weakest promptable dimension = `persuasive_coherence` @ 4.82 ≥ 4.8 pre-registered
ceiling.** The only sub-ceiling dimension is `grounding` (3.0), which is corpus-bound
and off-limits to an offline prompt edit.

## Decision (honest-result clause)
**No promotion.** `drafter_v2` stays active. We did NOT manufacture a `drafter_v3`:
on this larger sample, `drafter_v2`'s general appeal-vector/procedural-audit reflection
from Run #1 already generalizes to every prompt-movable dimension. The single
persuasive_coherence ding was a case-specific padding issue, not a systematic,
prompt-addressable gap (the prompt already mandates a calm, structured, non-padded
letter).

## What this confirms / unlocks
- Run #1's +20.5% lift was not a 4-case artifact — `drafter_v2` holds at the promptable
  ceiling across a 2.75× larger train signal.
- The remaining offline gap is entirely `grounding`, which needs **live corpus
  retrieval (Tier 1)** — or genuinely harder cases — to open further headroom.
- These prompts (`drafter_v2`) are the starting point for the Tier-1 live re-run
  (Gemini drafting + an independent judge + κ≥0.6 calibration), where `grounding`
  becomes addressable.

Firewall (INV-2): drafter subagents received only the student packet; the judges'
laundered improvement_notes (general craft guidance, no answer-key specifics) were the
only judge output that reached this record.
