/**
 * Judge-facing copy for `/showcase`. Serif = story; mono = machine telemetry.
 * Showcase may name Phoenix, judges, GEPA — unlike `/appeal` (see design-brief §4).
 */

/** Hero word-by-word headline (GSAP reveal). */
export const HERO_HEADLINE_L1 = ["They", "have", "algorithms."] as const;
export const HERO_HEADLINE_L2 = ["Now", "you", "do", "too."] as const;

export const HERO_EYEBROW = "AEGIS · LIVE LEARNING OBSERVATORY";

export const HERO_SUBHEAD_P1 =
  "US health insurers deny roughly 19% of in-network claims (about 73 million a year on ACA exchanges alone). When patients file appeals, 1 in 3 succeed — but <strong>fewer than 1% appeal</strong>.";

export const HERO_SUBHEAD_P2 =
  "The asymmetry is structural: insurers automate denial through AI-powered adjudication and prior authorization algorithms, while patients face a thirty-page policy document and a phone tree. Aegis helps solve this asymmetry.";

export const HERO_CTA = "Start preview run";

export const HERO_TELEMETRY = [
  "HOLDOUT · baseline measure · no learning yet",
  "GEPA · reflective mutation on train failures",
  "JUDGES · six dimensions · laundered feedback in",
  "GATE · GEPA proposal · waiting for approval",
  "COMPOSITE · 0.40 → 0.75 on held-out",
  "PHOENIX · traces ingested · memory eligible",
] as const;

export const THESIS_STATEMENT =
  "Most appeal tools are frozen in time — same prompt, same blind spots.";

export const THESIS_TURN =
  "Aegis learns from its Arize Phoenix traces and can be trained to improve its own prompts and insurer playbooks.";

export const THESIS_STATIC_LABEL = "Fixed prompt";
export const THESIS_STATIC_CAPTION = "One version. No feedback loop.";

export const THESIS_AEGIS_LABEL = "Aegis";
export const THESIS_AEGIS_CAPTION = "GEPA evolves the prompt from past judge scores.";

export const THESIS_FORESHADOW =
  "Phoenix MCP is structurally load-bearing in Aegis — training signal and runtime memory flow through Phoenix";

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
    body: "Review proposed changes to the drafter, question agent, slice playbooks, and US rules.",
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
export const DOCK_ROLLBACK = "Rollback last promotion";

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
  promote: "Shipping the GEPA-approved prompt, question-agent, and playbook changes.",
  measure_after: "Re-scoring holdout with the promoted version.",
  failed: "Run stopped. See the error below.",
  cancelled: "Cancelled. Nothing was promoted.",
  rejected: "Proposal discarded. Production prompt unchanged.",
  rolled_back: "Previous prompt and playbook restored.",
};

export const APPROVE_CTA = "Promote GEPA proposal";
export const REVIEW_PROMOTION_CTA = "Review proposed changes";
export const PROMOTION_REVIEW_EYEBROW = "GEPA PROPOSAL";
export const PROMOTION_REVIEW_HEADLINE = "Review before you ship";
export const PROMOTION_REVIEW_LEAD =
  "Scroll through every proposed change. Nothing promotes until you approve here.";
export const REJECT_CTA = "Discard proposal";
export const CANCEL_CTA = "Cancel run";
export const RESUME_CTA = "Resume from checkpoint";

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
export const BEFORE_AFTER_HEADLINE = "Better appeals after learning.";

export const CASE_CYCLER_LABEL = "Sample case";
export const CASE_DENIAL_LETTER_PILL = "Denial letter";
export const CASE_CLINICAL_CONTEXT_PILL = "Clinical context";
export const CASE_DENIAL_LETTER_MODAL_EYEBROW = "DENIAL LETTER";
export const CASE_CLINICAL_CONTEXT_MODAL_EYEBROW = "CLINICAL CONTEXT";

export const VERSUS_LIFT_LABEL = "Held-out lift";
export const VERSUS_DRAFT_BEFORE = "Before learning";
export const VERSUS_DRAFT_AFTER = "After learning";
export const VERSUS_ILLUSTRATIVE =
  "No recorded before/after run for this case yet. Held-out lift stays at 0% until a credentialed eval is captured.";
export const VERSUS_PENDING = "AWAITING MEASUREMENT";
export const VERSUS_PHOENIX_LINK = "Open trace in Phoenix";
export const VERSUS_RUN_SIMULATOR = "Run simulator";
export const VERSUS_MEASURE_RUNNING =
  "Drafting appeal and running the outcome simulator — typically 1–3 minutes. Do not close this tab.";
export const VERSUS_BACKEND_REQUIRED =
  "Measured lift needs the live API. Open Settings (gear) and confirm the backend URL; the status dot should be green.";
export const VERSUS_VIEW_DRAFT = "View appeal draft";
export const VERSUS_HELD_OUT_COMPOSITE = "Held-out composite";
export const VERSUS_SIMULATOR_SCORE = "Simulator score";
export const VERSUS_HELD_OUT_VERDICT_APPROVE = "HELD-OUT · APPROVE";
export const VERSUS_HELD_OUT_VERDICT_DENY = "HELD-OUT · DENY";
export const VERSUS_SIMULATOR_APPROVED = "APPROVED";
export const VERSUS_SIMULATOR_REJECTED = "REJECTED";
export const VERSUS_AFTER_LOCKED =
  "Unlocks after you approve a GEPA proposal from a preview or production run.";
export const VERSUS_DRAFT_MODAL_EYEBROW = "APPEAL DRAFT";
export const SIMULATOR_MODAL_EYEBROW = "OUTCOME SIMULATOR";
export const SIMULATOR_MODAL_SCORE = "Simulator score (v2 strict)";
export const SIMULATOR_MODAL_FEATURES = "Feature anchors";
export const SIMULATOR_MODAL_PROXY =
  "A transparent rule-based proxy — not a prediction of what the insurer will do.";
export const SIMULATOR_MODAL_GAPS = "What would make this stronger";
export const SIMULATOR_MODAL_CRITIQUE = "Summary";

export const DIFF_EYEBROW = "GEPA · REFLECTIVE MUTATION";
export const DIFF_HEADLINE = "What GEPA changed in the proposal";

export const INTELLIGENCE_EYEBROW = "GEPA · THE LEARNING LOOP";
export const INTELLIGENCE_HEADLINE = "Train, evolve, remember.";
export const INTELLIGENCE_BODY =
  "During Training every appeal draft is graded on six dimensions — one faithfulness hard gate plus five weighted scores. When scores land in Phoenix, GEPA reads that feedback and mutates the drafter prompt, question-agent prompt, insurer playbooks, and US federal rulebook. The result is a sample-efficient, reflective evolution, not gradient descent.";

export const GEPA_SPOTLIGHT_EYEBROW = "GEPA · REFLECTIVE PROMPT EVOLUTION";
export const GEPA_SPOTLIGHT_HEADLINE = "Judge feedback becomes the next prompt.";
export const GEPA_SPOTLIGHT_BODY =
  "GEPA (Reflective Prompt Evolution) is the learning engine under the hood — an evolutionary optimizer that reads natural-language judge notes and proposes targeted edits. It is a way to retrain Aegis for new insurers, even geography without losing previous learning.";
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
  {
    kind: "draft" as const,
    label: "Draft",
    callout: "The drafter agent turns denial context into a first-pass appeal letter.",
  },
  {
    kind: "judge" as const,
    label: "Judge panel",
    callout: "Six dimensions — one faithfulness hard gate, five weighted scores.",
  },
  {
    kind: "memory" as const,
    label: "Phoenix memory",
    callout: "Judge scores and notes land here — the reflection agent reads them to propose the next edit.",
  },
  {
    kind: "optimize" as const,
    label: "GEPA",
    callout:
      "Reflective edits to prompts and playbooks from judge feedback — GEPA held-out cases must lift first.",
  },
  {
    kind: "approve" as const,
    label: "Your approval",
    callout: "Nothing ships until you approve the proposed prompt and playbook changes.",
  },
  {
    kind: "promote" as const,
    label: "Promote",
    callout: "Approved changes replace the active production playbook set.",
  },
] as const;
