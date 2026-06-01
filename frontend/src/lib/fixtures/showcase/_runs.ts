import run1 from "../../../../tests-data/recorded/efficacy_run1.json";

export const RUN1 = run1 as {
  baseline_composite: number;
  optimized_composite: number;
  lift_relative_pct: number;
  per_case: Record<string, { v1: number; v2: number }>;
};

export const COUNTERFACTUAL = { on_composite: 0.88, off_composite: 0.42 }; // design-target; labeled in UI
