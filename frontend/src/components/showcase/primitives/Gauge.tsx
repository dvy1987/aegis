"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/cn";
import { EASE_OUT_EXPO } from "@/lib/motion";

type GaugeTone = "accent" | "deny" | "warn";

const toneVar: Record<GaugeTone, string> = {
  accent: "var(--sc-accent)",
  deny: "var(--sc-deny)",
  warn: "var(--sc-warn)",
};

/**
 * Horizontal composite-quality bar (0–1). Fills with an eased sweep on enter.
 * `threshold` draws a static tick the fill can reach past.
 */
export function Gauge({
  value,
  label,
  threshold,
  tone = "accent",
  showValue = true,
  live = false,
  className,
}: {
  value: number;
  label?: string;
  threshold?: number;
  tone?: GaugeTone;
  showValue?: boolean;
  /** When true, animates to `value` on every change (can retreat), not just on enter. */
  live?: boolean;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const clamped = Math.max(0, Math.min(1, value));
  const pct = clamped * 100;
  const color = toneVar[tone];

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {label && (
        <span className="sc-label" style={{ letterSpacing: "0.12em" }}>
          {label}
        </span>
      )}
      <div
        className="relative h-2 w-full overflow-hidden rounded-full"
        style={{ background: "var(--sc-bg-sunken)" }}
        role="meter"
        aria-valuenow={Number(clamped.toFixed(2))}
        aria-valuemin={0}
        aria-valuemax={1}
        aria-label={label}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 12px ${color}` }}
          initial={live ? false : { width: 0 }}
          animate={live ? { width: `${pct}%` } : undefined}
          whileInView={live ? undefined : { width: `${pct}%` }}
          viewport={live ? undefined : { once: true, amount: 0.6 }}
          transition={reduce ? { duration: 0 } : { duration: 0.95, ease: EASE_OUT_EXPO }}
        />
        {threshold != null && (
          <span
            aria-hidden
            className="absolute top-[-2px] h-3 w-px"
            style={{
              left: `${Math.max(0, Math.min(1, threshold)) * 100}%`,
              background: "var(--sc-hairline-strong)",
            }}
          />
        )}
      </div>
      {showValue && (
        <span className="sc-mono" style={{ color: "var(--sc-text-3)" }}>
          {clamped.toFixed(2)}
          {threshold != null ? ` · threshold ${threshold.toFixed(2)}` : ""}
        </span>
      )}
    </div>
  );
}
