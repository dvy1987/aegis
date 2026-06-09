import type { Variants } from "framer-motion";

import { BEAT_MS, DUR, EASE_OUT_EXPO, STAGGER } from "./easings";

const easeOutExpo = EASE_OUT_EXPO;

/** Tier 2 — section entrance (12–16px rise + fade + blur-in). */
export const sectionEnter: Variants = {
  hidden: {
    opacity: 0,
    y: 14,
    filter: "blur(8px)",
  },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      duration: DUR.narrativeMin / 1000,
      ease: easeOutExpo,
      when: "beforeChildren",
      staggerChildren: STAGGER.sectionChild / 1000,
    },
  },
};

export const sectionChild: Variants = {
  hidden: { opacity: 0, y: 12, filter: "blur(8px)" },
  visible: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: DUR.subtleMax / 1000, ease: easeOutExpo },
  },
};

/** Stagger container for nested reveals. */
export const staggerChildren: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: STAGGER.sectionChild / 1000,
      delayChildren: 0.04,
    },
  },
};

/** Run control dock — recomposes between idle / running / approval states. */
export const dockState: Variants = {
  idle: {
    opacity: 1,
    y: 0,
    transition: { duration: DUR.narrativeMin / 1000, ease: easeOutExpo },
  },
  running: {
    opacity: 1,
    y: 0,
    transition: { duration: DUR.narrativeMin / 1000, ease: easeOutExpo },
  },
  needsApproval: {
    opacity: 1,
    y: 0,
    transition: { duration: DUR.narrativeMax / 1000, ease: easeOutExpo },
  },
  success: {
    opacity: 1,
    y: 0,
    transition: { duration: DUR.narrativeMin / 1000, ease: easeOutExpo },
  },
  error: {
    opacity: 1,
    y: 0,
    transition: { duration: DUR.narrativeMin / 1000, ease: easeOutExpo },
  },
};

/** Run status panel — stage heading morph (crossfade + 8px rise). */
export const statusMorph: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: DUR.subtleMax / 1000, ease: easeOutExpo },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: DUR.subtleMin / 1000, ease: easeOutExpo },
  },
};

/** Approval buttons — rise in with accent ring beat. */
export const approvalReveal: Variants = {
  hidden: { opacity: 0, y: 12, scale: 0.98 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: BEAT_MS / 2000, ease: easeOutExpo },
  },
};

/** Verdict cells — fade + scale in as poll data arrives. */
export const verdictCellEnter: Variants = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: DUR.subtleMin / 1000, ease: easeOutExpo },
  },
};
