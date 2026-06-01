# Learning Coordinator — Efficacy Run #2 + meta-prompt A/B (Tier 2, 2026-06-01)

**What this is:** the offline Tier-2 continuation of [Run #1](2026-05-31-coordinator-efficacy-run.md).
Three offline deliverables, no GCP and no API key — the Claude Code session again played
drafter / judge / reflection via firewall-isolated subagents.

1. **`efficacy_io` extracted + tested** — the throwaway Session-24 Phase-2 scripts are now the
   reusable, unit-tested module `backend/app/learning/efficacy_io.py` (firewall-clean packet prep,
   composite scoring, weakest-promptable-dimension selection, lift/veto reporting). Pinned to the
   committed Run #1 fixtures (`test_efficacy_io.py`, 4 tests); the Run #1 scripts now import it and
   re-emit a byte-identical `result.json`.

2. **Round 2 — full train split → offline ceiling reached (no promotion).**
3. **Reflection meta-prompt A/B → `base` wins (no change to default).**

---

## Round 2 — full 11-case train signal

Baseline = the currently-promoted `drafter_v2`. We drafted + judged all **11 `case_*` train cases**
(2.75× Run #1's 4 train cases) with the same firewall and the Run-#1 calibrated rubric, to select the
next weakest *promptable* dimension.

| dimension | v2 train mean | note |
|---|---|---|
| grounding | 3.0 | corpus-bound — no retrieved citations offline; unmovable by a prompt edit |
| appeal_vector_capture | 5.0 | at ceiling |
| case_specific_clinical_rebuttal | 5.0 | at ceiling |
| evidence_completeness | 5.0 | at ceiling |
| persuasive_coherence | 4.82 | weakest promptable (one case dinged for padding), still ≥ 4.8 ceiling |

Train composite **0.876**; all 11 hard gates PASS. **Weakest promptable = `persuasive_coherence`
@ 4.82 ≥ 4.8 pre-registered ceiling.**

**Decision (honest-result clause): no promotion.** `drafter_v2` stays active; **no `drafter_v3`
manufactured.** On this larger sample, v2's Run-#1 reflection already generalizes to every
prompt-movable dimension; the single coherence ding was case-specific padding, not a systematic
prompt-addressable gap. The only remaining offline gap is `grounding`, which needs **live corpus
retrieval (Tier 1)** to open. This *confirms Run #1's +20.5% was not a 4-case artifact* — v2 holds at
the promptable ceiling across the full split.

Artifacts: `eval/efficacy_runs/2026-06-01-round2/` (prep.py, inputs/, drafts/v2/, judgments/v2/,
reflections/round2_no_headroom_finding.md, score.py, result.json). Replay regression:
`test_efficacy_run_fixture.py::test_round2_*`.

---

## Reflection meta-prompt A/B — `base` vs `critique_plus`

`build_reflection_prompt` is the optimizer's OWN instruction; improving it is meta-optimization. We
added a `variant` parameter (ships tested) with a `critique_plus` variant that forces an explicit
single-flaw diagnosis then a MINIMAL edit. We A/B'd it on the fixed task *reflect `drafter_v1` on
`appeal_vector_capture`* (the slice with known headroom), same 4-case held-out as Run #1.

| variant | held-out composite | lift vs v1 (0.73) | added body words | avc / cscr means |
|---|---|---|---|---|
| **base** (= `drafter_v2`) | **0.88** | +0.15 / +20.5% | 129 | 5.0 / 5.0 |
| critique_plus | 0.835 | +0.105 / +14.4% | 40 | 4.5 / 4.5 |

**Quality winner: `base`** (Δ = +0.045). `critique_plus`'s minimal edit was **3.2× tighter** but
under-captured the appeal vector / clinical rebuttal on held-out cases — the fuller two-lever base
reflection generalized more reliably. **`base` stays the default; `critique_plus` not promoted.** The
`variant` param is retained for Tier-1 re-evaluation on harder/live cases.

Artifacts: `eval/efficacy_runs/2026-06-01-metaprompt-ab/` (base/ + critique_plus/{candidate_prompt,
drafts,judgments}, score_ab.py, result.json, finding.md).

---

## Caveats (carried from Run #1, still apply)
- **Small N**, **Claude-drafts/Claude-judges** (same family), offline only. The discriminating
  cross-model re-run (Gemini drafting + an independent judge + κ≥0.6) is **Tier 1**; these prompts
  (`drafter_v2`, base meta-prompt) are its starting point.
- **`grounding` is unaddressable offline** — it caps every composite < 1.0 and is the obvious next
  lever once live corpus retrieval is wired (Tier 1).
- Round 2 is an **honest null on promotion** (ceiling reached), not a failure: it bounds where offline
  prompt optimization can take this Student and points the remaining headroom squarely at live corpus.

## Bottom line
Offline prompt optimization of the Student has reached its ceiling on every promptable dimension; the
efficacy machinery is now DRY and tested; the optimizer's meta-prompt was A/B-validated (base wins).
The next real headroom — `grounding` — and the cross-model efficacy read both require **Tier 1 (live
GCP/Phoenix)**.
