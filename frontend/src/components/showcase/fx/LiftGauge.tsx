"use client";

import { useRef } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/cn";
import { MetricCounter } from "@/components/showcase/primitives/MetricCounter";

/**
 * Fallback lift gauge — a semicircular needle gauge that sweeps to `value`
 * (a percent) with a spring overshoot, plus a luminous count-up readout.
 */
export function LiftGauge({
  value,
  max = 100,
  className,
}: {
  value: number;
  max?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const frac = Math.max(0, Math.min(1, value / max));
  // -90deg (empty) → +90deg (full)
  const angle = -90 + frac * 180;

  return (
    <div ref={ref} className={cn("flex flex-col items-center gap-1", className)}>
      <svg viewBox="0 0 200 116" className="w-full max-w-[220px]" aria-hidden role="img">
        {/* track */}
        <path
          d="M 16 100 A 84 84 0 0 1 184 100"
          fill="none"
          stroke="var(--sc-bg-sunken)"
          strokeWidth={10}
          strokeLinecap="round"
        />
        {/* fill */}
        <motion.path
          d="M 16 100 A 84 84 0 0 1 184 100"
          fill="none"
          stroke="var(--sc-accent)"
          strokeWidth={10}
          strokeLinecap="round"
          style={{ filter: "drop-shadow(0 0 8px var(--sc-accent-glow))" }}
          initial={{ pathLength: reduce ? frac : 0 }}
          animate={inView ? { pathLength: frac } : {}}
          transition={reduce ? { duration: 0 } : { duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
        />
        {/* needle */}
        <motion.g
          initial={{ rotate: reduce ? angle : -90 }}
          animate={inView ? { rotate: angle } : {}}
          transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 90, damping: 11, mass: 0.8 }}
          style={{ transformOrigin: "100px 100px" }}
        >
          <line x1={100} y1={100} x2={100} y2={32} stroke="var(--sc-text)" strokeWidth={2.5} strokeLinecap="round" />
        </motion.g>
        <circle cx={100} cy={100} r={6} fill="var(--sc-text)" />
      </svg>
      <div className="flex items-baseline gap-1">
        <span className="sc-c-accent" style={{ fontFamily: "var(--font-mono)", fontSize: "2rem", fontWeight: 600 }}>
          +
        </span>
        <MetricCounter
          to={value}
          decimals={value % 1 === 0 ? 0 : 1}
          suffix="%"
          className="sc-c-accent"
          style={{ fontSize: "2rem", fontWeight: 600, letterSpacing: "0" }}
        />
      </div>
    </div>
  );
}
