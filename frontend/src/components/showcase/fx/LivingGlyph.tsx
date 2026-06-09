"use client";

import { useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/cn";
import { EASE_OUT_EXPO } from "@/lib/motion";

type GlyphState = "idle" | "ignite" | "settled";

/**
 * Fallback "living glyph" — an abstract aegis eye/shield built from concentric
 * arcs of evidence around a luminous iris. Breathes when idle, draws itself in
 * on `ignite`, brightens on `settled`. Cursor parallax ≤6px. SVG + framer only.
 */
export function LivingGlyph({
  state = "idle",
  parallax = true,
  className,
}: {
  state?: GlyphState;
  parallax?: boolean;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const settled = state === "settled";
  const igniting = state === "ignite";

  function onPointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    if (!parallax || reduce || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
    const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
    setOffset({ x: Math.max(-1, Math.min(1, dx)) * 6, y: Math.max(-1, Math.min(1, dy)) * 6 });
  }

  const drawTransition = reduce
    ? { duration: 0 }
    : { duration: 1.2, ease: EASE_OUT_EXPO };

  const rings = [148, 120, 92];
  const ticks = Array.from({ length: 36 }, (_, i) => i);

  return (
    <div
      ref={ref}
      className={cn("relative aspect-square w-full max-w-[420px]", className)}
      onPointerMove={onPointerMove}
      onPointerLeave={() => setOffset({ x: 0, y: 0 })}
    >
      <motion.div
        className="h-full w-full"
        animate={{ x: offset.x, y: offset.y }}
        transition={{ type: "spring", stiffness: 60, damping: 18 }}
      >
        <motion.div
          className={cn("h-full w-full", !reduce && !igniting && "sc-breath")}
          animate={{ opacity: settled ? 1 : 0.92, scale: settled ? 1.02 : 1 }}
          transition={{ duration: 0.8, ease: EASE_OUT_EXPO }}
        >
          <svg viewBox="0 0 360 360" className="h-full w-full" aria-hidden role="img">
            <defs>
              <radialGradient id="sc-iris" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--sc-accent)" stopOpacity={settled ? 1 : 0.9} />
                <stop offset="55%" stopColor="var(--sc-accent)" stopOpacity="0.35" />
                <stop offset="100%" stopColor="var(--sc-accent)" stopOpacity="0" />
              </radialGradient>
            </defs>

            {/* evidence ticks */}
            <g>
              {ticks.map((i) => {
                const a = (i / ticks.length) * Math.PI * 2;
                const r1 = 162;
                const r2 = i % 3 === 0 ? 150 : 156;
                return (
                  <motion.line
                    key={i}
                    x1={180 + Math.cos(a) * r1}
                    y1={180 + Math.sin(a) * r1}
                    x2={180 + Math.cos(a) * r2}
                    y2={180 + Math.sin(a) * r2}
                    stroke="var(--sc-text-3)"
                    strokeWidth={1}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: settled ? 0.7 : 0.4 }}
                    transition={{ duration: 0.6, delay: igniting ? 0.6 + i * 0.01 : 0 }}
                  />
                );
              })}
            </g>

            {/* concentric arcs (the rings of evidence) */}
            {rings.map((r, idx) => (
              <motion.circle
                key={r}
                cx={180}
                cy={180}
                r={r}
                fill="none"
                stroke={idx === 0 ? "var(--sc-accent-dim)" : "var(--sc-hairline-strong)"}
                strokeWidth={idx === 0 ? 1.5 : 1}
                initial={{ pathLength: igniting ? 0 : 1, opacity: igniting ? 0 : 1 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ ...drawTransition, delay: igniting ? idx * 0.18 : 0 }}
              />
            ))}

            {/* iris glow */}
            <motion.circle
              cx={180}
              cy={180}
              r={70}
              fill="url(#sc-iris)"
              initial={{ opacity: igniting ? 0 : 1, scale: igniting ? 0.6 : 1 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.9, ease: EASE_OUT_EXPO, delay: igniting ? 0.5 : 0 }}
              style={{ transformOrigin: "180px 180px" }}
            />
            {/* iris core */}
            <motion.circle
              cx={180}
              cy={180}
              r={settled ? 22 : 18}
              fill="var(--sc-accent)"
              initial={{ opacity: igniting ? 0 : 1 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: igniting ? 0.9 : 0 }}
              style={{ filter: "drop-shadow(0 0 14px var(--sc-accent-glow))" }}
            />
          </svg>
        </motion.div>
      </motion.div>
    </div>
  );
}
