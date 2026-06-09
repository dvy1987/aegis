"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { animate, useInView, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/cn";
import { BEAT_MS, EASE_OUT_EXPO } from "@/lib/motion";

/**
 * Eased count-up. Animates `from → to` when scrolled into view.
 * Reduced-motion shows the final value immediately.
 */
export function MetricCounter({
  to,
  from = 0,
  decimals = 0,
  prefix = "",
  suffix = "",
  delay = 0,
  className,
  style,
}: {
  to: number;
  from?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  delay?: number;
  className?: string;
  style?: CSSProperties;
}) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.6 });
  const [value, setValue] = useState(from);

  useEffect(() => {
    if (!inView) return;
    const controls = animate(from, to, {
      duration: reduce ? 0 : BEAT_MS / 1000,
      ease: EASE_OUT_EXPO,
      delay: reduce ? 0 : delay,
      onUpdate: (v) => setValue(v),
    });
    return () => controls.stop();
  }, [inView, reduce, to, from, delay]);

  return (
    <span ref={ref} className={cn("sc-mono tabular-nums", className)} style={style}>
      {prefix}
      {value.toFixed(decimals)}
      {suffix}
    </span>
  );
}
