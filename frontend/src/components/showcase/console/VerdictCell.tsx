"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/cn";
import { EASE_OUT_EXPO } from "@/lib/motion";

/**
 * Luminous status tile. APPROVE → accent, DENY → deny, anything else → pending.
 * Colour is never the only signal — the title carries case id + verdict.
 */
export function VerdictCell({
  verdict,
  caseId,
  index = 0,
}: {
  verdict: string;
  caseId: string;
  index?: number;
}) {
  const reduce = useReducedMotion();
  const v = (verdict || "").toUpperCase();
  const approved = v === "APPROVE";
  const denied = v === "DENY";
  const tone = approved ? "sc-cell--approve" : denied ? "sc-cell--deny" : "sc-cell--pending";

  return (
    <motion.span
      title={`${caseId}: ${v || "pending"}`}
      aria-label={`${caseId}: ${v || "pending"}`}
      className={cn("sc-cell block min-w-5", tone)}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={
        reduce
          ? { duration: 0 }
          : { duration: 0.28, ease: EASE_OUT_EXPO, delay: Math.min(index, 14) * 0.025 }
      }
    />
  );
}
