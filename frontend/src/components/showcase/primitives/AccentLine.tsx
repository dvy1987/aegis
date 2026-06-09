"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/cn";
import { EASE_OUT_EXPO } from "@/lib/motion";

/** A hairline that "draws" itself (scaleX/scaleY) on reveal. */
export function AccentLine({
  orientation = "horizontal",
  tone = "accent",
  delay = 0,
  className,
}: {
  orientation?: "horizontal" | "vertical";
  tone?: "accent" | "hairline";
  delay?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const horizontal = orientation === "horizontal";
  const color = tone === "accent" ? "var(--sc-accent)" : "var(--sc-hairline-strong)";

  return (
    <motion.span
      aria-hidden
      className={cn("block", horizontal ? "h-px w-full" : "w-px h-full", className)}
      style={{
        background: color,
        transformOrigin: horizontal ? "left center" : "top center",
        boxShadow: tone === "accent" ? "0 0 10px var(--sc-accent-glow)" : undefined,
      }}
      initial={{ scaleX: horizontal ? 0 : 1, scaleY: horizontal ? 1 : 0 }}
      whileInView={{ scaleX: 1, scaleY: 1 }}
      viewport={{ once: true, amount: 0.8 }}
      transition={reduce ? { duration: 0 } : { duration: 0.7, ease: EASE_OUT_EXPO, delay }}
    />
  );
}
