/**
 * Showcase cinematic motion constants.
 * Source: docs/2026-06-08-showcase-cinematic-redesign-plan.md §3–§10
 */

/** Primary out-expo curve for Tier 1–2 motion. */
export const EASE_OUT_EXPO = [0.22, 1, 0.36, 1] as const;

/** Narrative beat length for Tier 3 camera moments (~1.2–2.0s). */
export const BEAT_MS = 1400;

export const DUR = {
  subtleMin: 240,
  subtleMax: 520,
  narrativeMin: 400,
  narrativeMax: 600,
  theatrical: BEAT_MS,
} as const;

export const STAGGER = {
  sectionChild: 70,
  verdictCell: 60,
} as const;

/** CSS custom property name consumed by showcase styles. */
export const SC_BEAT_VAR = "--sc-beat";

export const scBeatStyle = {
  [SC_BEAT_VAR]: `${BEAT_MS}ms`,
} as const;
