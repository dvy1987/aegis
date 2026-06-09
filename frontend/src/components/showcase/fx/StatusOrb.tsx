"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/cn";

export type OrbTone = "idle" | "running" | "approval" | "success" | "error";

/** Maps a raw run-session status to an orb tone. */
export function toneForStatus(status?: string | null): OrbTone {
  switch (status) {
    case "running":
    case "queued":
    case "promoted":
      return "running";
    case "needs_approval":
      return "approval";
    case "successful":
      return "success";
    case "failed":
    case "cancelled":
    case "rejected":
      return "error";
    default:
      return "idle";
  }
}

const toneColor: Record<OrbTone, string> = {
  idle: "var(--sc-text-3)",
  running: "var(--sc-accent)",
  approval: "var(--sc-warn)",
  success: "var(--sc-accent)",
  error: "var(--sc-deny)",
};

/** Fallback status orb — color + pulse rate driven by run state. */
export function StatusOrb({
  status,
  size = 14,
  className,
}: {
  status?: string | null;
  size?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const tone = toneForStatus(status);
  const color = toneColor[tone];
  const pulsing = (tone === "running" || tone === "approval") && !reduce;
  const period = tone === "running" ? 1.4 : 2.2;

  return (
    <span
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size * 2, height: size * 2 }}
      role="status"
      aria-label={`Run state: ${tone}`}
    >
      {pulsing && (
        <motion.span
          className="absolute rounded-full"
          style={{ width: size, height: size, background: color }}
          initial={{ opacity: 0.5, scale: 1 }}
          animate={{ opacity: 0, scale: 2.4 }}
          transition={{ duration: period, repeat: Infinity, ease: "easeOut" }}
        />
      )}
      <motion.span
        className="relative rounded-full"
        style={{ width: size, height: size, background: color, boxShadow: `0 0 12px ${color}` }}
        animate={pulsing ? { opacity: [0.7, 1, 0.7] } : { opacity: 1 }}
        transition={pulsing ? { duration: period, repeat: Infinity, ease: "easeInOut" } : { duration: 0.3 }}
      />
    </span>
  );
}
