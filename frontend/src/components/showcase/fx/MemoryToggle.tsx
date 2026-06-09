"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/cn";

/**
 * Fallback memory switch — an accessible `role="switch"` button with a weighty
 * knob travel. "On" glows accent; "off" goes inert. The dependent panel decay
 * is handled by the consumer (Act V) via the emitted `onChange`.
 */
export function MemoryToggle({
  on,
  onChange,
  label = "Phoenix memory",
  className,
}: {
  on: boolean;
  onChange: (next: boolean) => void;
  label?: string;
  className?: string;
}) {
  const reduce = useReducedMotion();

  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={`${label}: ${on ? "on" : "off"}`}
      onClick={() => onChange(!on)}
      className={cn(
        "group inline-flex items-center gap-3 rounded-full focus-visible:outline-2 focus-visible:outline-offset-2",
        className,
      )}
      style={{ outlineColor: "var(--sc-accent)" }}
    >
      <span
        className="relative flex h-8 w-14 items-center rounded-full border px-1 transition-colors"
        style={{
          background: on ? "color-mix(in oklch, var(--sc-accent) 22%, var(--sc-bg-sunken))" : "var(--sc-bg-sunken)",
          borderColor: on ? "var(--sc-accent)" : "var(--sc-hairline-strong)",
          boxShadow: on ? "0 0 16px var(--sc-accent-glow)" : "none",
        }}
      >
        <motion.span
          className="block h-6 w-6 rounded-full"
          style={{
            background: on ? "var(--sc-accent)" : "var(--sc-text-3)",
            boxShadow: on ? "0 0 10px var(--sc-accent-glow)" : "none",
          }}
          animate={{ x: on ? 24 : 0 }}
          transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 420, damping: 30, mass: 0.9 }}
        />
      </span>
      <span className="sc-label" style={{ color: on ? "var(--sc-text-2)" : "var(--sc-text-3)" }}>
        {label} · {on ? "ON" : "OFF"}
      </span>
    </button>
  );
}
