/**
 * Judge-facing copy for `/showcase`. Serif = story; mono = machine telemetry.
 * Showcase may name Phoenix, judges, GEPA — unlike `/appeal` (see design-brief §4).
 */

/** Hero word-by-word headline (GSAP reveal). */
export const HERO_HEADLINE = ["Every", "score", "rewrites", "the", "next", "draft."] as const;

export const HERO_EYEBROW = "AEGIS · LIVE LEARNING OBSERVATORY";

export const HERO_SUBHEAD =
  "Ten real denial cases. A held-out benchmark the model never trains on. GEPA turns judge feedback into prompt and playbook edits — then pauses for your approval before anything ships. Scroll to see measured lift — or start a preview run below.";

export const HERO_CTA = "Start preview run";

export const HERO_TELEMETRY = [
  "HOLDOUT · baseline measure · no learning yet",
  "GEPA · reflective mutation on train failures",
  "JUDGES · seven dimensions · laundered feedback in",
  "GATE · GEPA proposal · waiting for approval",
  "COMPOSITE · 0.40 → 0.75 on held-out",
  "PHOENIX · traces ingested · memory eligible",
] as const;

export const THESIS_STATEMENT =
  "Most appeal tools ship frozen — same prompt, same blind spots, year after year.";

export const THESIS_TURN =
  "Aegis reads what it already scored, then drafts the next case with that history in hand.";

export const THESIS_STATIC_LABEL = "Fixed prompt";
export const THESIS_STATIC_CAPTION = "One version. No feedback loop.";

export const THESIS_AEGIS_LABEL = "Aegis";
export const THESIS_AEGIS_CAPTION = "GEPA evolves the prompt from past judge scores.";

export const THESIS_FORESHADOW =
  "Proof ahead — we cut Phoenix memory off and show the score drop. If it does not fall, the thesis fails.";

export const INSTRUMENT_EYEBROW = "LIVE LEARNING CONSOLE";
export const INSTRUMENT_HEADLINE = "Watch the learning unfold live.";
export const INSTRUMENT_LEAD = "Every run from this panel follows the same arc.";

export const INSTRUMENT_STEPS = [
  {
    title: "Holdout baseline",
    body: "Score the drafter first with learning off.",
  },
  {
    title: "GEPA Learning",
    body: "GEPA runs on training slice and learns from Phoenix traces.",
  },
  {
    title: "Review Proposal",
    body: "Review suggested improvements to the appeal drafting agent.",
  },
  {
    title: "Holdout Lift",
    body: "Re-score holdout cases to confirm lift after promotion.",
  },
] as const;

export const DOCK_EYEBROW = "SESSION CONTROLS";
export const DOCK_HEADLINE = "Ship only what's best in class.";
export const DOCK_QUICK_TITLE = "Preview run";
export const DOCK_SERIOUS_TITLE = "Production run";
export const DOCK_QUICK_CTA = "Start preview run";
export const DOCK_SERIOUS_CTA = "Start production run";
export const DOCK_SERIOUS_LOCKED = "UNLOCKS AFTER PREVIEW RUN SUCCEEDS";
export const DOCK_ROLLBACK = "Restore previous prompt";

export const STATUS_EYEBROW = "SESSION STATUS";
export const STATUS_AWAITING = "Yet to start";
export const STATUS_JUST_NOW_EYEBROW = "JUST NOW";
export const STATUS_UP_NEXT_EYEBROW = "WHAT'S NEXT";

export const STAGE_CAPTIONS: Record<string, string> = {
  queued: "Queued on the server — work begins in the background.",
  measure_before: "Scoring holdout with today's prompt. Learning is off for this beat.",
  train_gepa:
    "Drafting and judging the train set. GEPA reads the failure pattern and proposes a new prompt and playbook.",
  waiting_for_approval: "GEPA proposal ready. Promote the rewrite, or discard it.",
  promote: "Shipping the GEPA-approved prompt and playbook.",
  measure_after: "Re-scoring holdout with the promoted version.",
  failed: "Run stopped. See the error below.",
  cancelled: "Cancelled. Nothing was promoted.",
  rejected: "Proposal discarded. Production prompt unchanged.",
  rolled_back: "Previous prompt and playbook restored.",
};

export const APPROVE_CTA = "Promote GEPA proposal";
export const REJECT_CTA = "Discard proposal";
export const CANCEL_CTA = "Cancel run";

export const MATRIX_EYEBROW = "EVIDENCE GRID";
export const MATRIX_HEADLINE = "Map how learning happens";
export const MATRIX_TAB_DEMO = "Preview";
export const MATRIX_TAB_SERIOUS = "Production";
export const MATRIX_QUICK_LOCKED = "Start a preview run to light this grid.";
export const MATRIX_SERIOUS_LOCKED = "Unlocks after preview run succeeds.";

export const MATRIX_PRE_TITLE = "Holdout cases · before learning";
export const MATRIX_PRE_CAPTION = "Drafter before training · baseline only";
export const MATRIX_TRAIN_BEFORE_TITLE = "Training cases · before learning";
export const MATRIX_TRAIN_BEFORE_CAPTION = "Baseline on training cases · learning off";
export const MATRIX_TRAIN_AFTER_TITLE = "Training cases · after learning";
export const MATRIX_TRAIN_AFTER_CAPTION = "Candidate agent · post-GEPA learning · not yet promoted";
export const MATRIX_POST_TITLE = "Holdout cases · after learning";
export const MATRIX_POST_CAPTION = "Drafter after training · post-approval";
export const MATRIX_WAIT_PRE = "Waiting for holdout baseline…";
export const MATRIX_WAIT_TRAIN = "Waiting for train-set measurements…";
export const MATRIX_WAIT_POST = "Waiting for your approval…";

export const BEFORE_AFTER_EYEBROW = "MEASURED LIFT";
export const BEFORE_AFTER_HEADLINE = "Same denial. Sharper letter.";

export const CASE_CYCLER_LABEL = "Sample case";

export const VERSUS_LIFT_LABEL = "Held-out lift";
export const VERSUS_DRAFT_BEFORE = "Before learning";
export const VERSUS_DRAFT_AFTER = "After learning";
export const VERSUS_ILLUSTRATIVE =
  "Illustrative for this case. Measured numbers appear where a live run is recorded.";
export const VERSUS_PHOENIX_LINK = "Open trace in Phoenix";

export const DIFF_EYEBROW = "GEPA · REFLECTIVE MUTATION";
export const DIFF_HEADLINE = "What GEPA changed in the proposal";

export const INTELLIGENCE_EYEBROW = "GEPA · THE LEARNING LOOP";
export const INTELLIGENCE_HEADLINE = "Score, remember, evolve — then you approve.";
export const INTELLIGENCE_BODY =
  "Every draft is graded on seven dimensions. Scores land in Phoenix. GEPA reads that feedback and mutates the drafter prompt and per-insurer playbooks — sample-efficient reflective evolution, not gradient descent. You approve before anything reaches production.";

export const GEPA_SPOTLIGHT_EYEBROW = "GEPA · REFLECTIVE PROMPT EVOLUTION";
export const GEPA_SPOTLIGHT_HEADLINE = "Judge feedback becomes the next prompt.";
export const GEPA_SPOTLIGHT_BODY =
  "GEPA (Reflective Prompt Evolution) is the learning engine under the hood — an evolutionary optimizer that reads natural-language judge notes and proposes targeted edits. It is what makes Aegis self-improving without retraining the model.";
export const GEPA_SPOTLIGHT_FOOTNOTE =
  "ICLR 2026 · sample-efficient vs RL · held-out generalization built in";

export const GEPA_PILLARS = [
  {
    title: "Reflective mutation",
    body: "An ADK reflector reads failing drafts plus laundered judge improvement notes — then proposes edited prompt and playbook text.",
  },
  {
    title: "Per-slice credit",
    body: "Mutates the module that actually failed: the global drafter prompt or one insurer×denial playbook — not a monolithic blob.",
  },
  {
    title: "Pareto frontier",
    body: "Tracks the best candidate per training case and samples from the non-dominated set — built-in anti-stagnation as the loop runs.",
  },
  {
    title: "Held-out gate",
    body: "Reflects on train failures; only proposals that lift the held-out benchmark survive to your approval screen.",
  },
] as const;

export const PIPELINE_NODES = [
  { kind: "draft" as const, label: "Draft" },
  {
    kind: "judge" as const,
    label: "Judge panel",
    callout: "Seven dimensions — two hard safety gates, five weighted scores. Six run as ADK agents.",
  },
  {
    kind: "memory" as const,
    label: "Phoenix memory",
    callout: "Past eval traces inform the next draft before the letter is written.",
  },
  {
    kind: "optimize" as const,
    label: "GEPA",
    callout:
      "Reflective mutation on judge feedback — evolves the drafter and per-slice playbooks, scored on held-out cases before promote.",
  },
  { kind: "approve" as const, label: "Your approval" },
  { kind: "promote" as const, label: "Promote" },
] as const;

export const COUNTERFACTUAL_EYEBROW = "MEMORY PROOF";
export const COUNTERFACTUAL_HEADLINE = "Cut the memory. Watch the score fall.";
export const COUNTERFACTUAL_BODY =
  "With Phoenix MCP on, Aegis pulls patterns from its own eval history. Off, it drafts blind — and the composite drops. That gap is the proof memory is load-bearing.";
export const COUNTERFACTUAL_MEMORY_ON = "MEMORY ON";
export const COUNTERFACTUAL_MEMORY_OFF = "MEMORY OFF · DEGRADED";
export const COUNTERFACTUAL_GAUGE_ON = "Composite · memory on";
export const COUNTERFACTUAL_GAUGE_OFF = "Composite · memory off";
export const COUNTERFACTUAL_FOOTNOTE =
  "Memory-off figure is a design target until a measured counterfactual run is recorded.";

export const MEMORY_TOGGLE_LABEL = "Phoenix memory";

export const IMPACT_EYEBROW = "WHY IT MATTERS";
export const IMPACT_HEADLINE =
  "Most denied claims are never appealed. Aegis keeps getting better at the drafting fight.";
export const IMPACT_METRIC_QUALITY = "Held-out composite · target";
export const IMPACT_METRIC_JUDGES = "Judge dimensions";
export const IMPACT_METRIC_APPROVAL = "Promotion gate";
export const IMPACT_METRIC_APPROVAL_VALUE = "REQUIRED";
export const IMPACT_ENDCARD =
  "AEGIS · Google ADK + Gemini · GEPA reflective evolution · observability by Arize Phoenix";
export const IMPACT_REPLAY = "Run again";
