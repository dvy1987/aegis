"use client";

import { motion, useReducedMotion } from "framer-motion";
import { EASE_OUT_EXPO } from "@/lib/motion";
import { DIFF_EYEBROW, DIFF_HEADLINE } from "@/components/showcase/copy";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";

/** "What changed, and why." — reflection notes that stagger in on enter. */
export function DiffCard({
  whatChanged,
  inactive = false,
}: {
  whatChanged: string[];
  inactive?: boolean;
}) {
  const reduce = useReducedMotion();
  if (!whatChanged.length) return null;
  return (
    <section
      className="flex flex-col gap-5"
      style={inactive ? { opacity: 0.45, filter: "saturate(0.35)" } : undefined}
      aria-disabled={inactive}
    >
      <div className="flex flex-col gap-1">
        <MonoLabel>{DIFF_EYEBROW}</MonoLabel>
        <h3 className="sc-h2" style={{ fontSize: "1.6rem" }}>
          {DIFF_HEADLINE}
        </h3>
      </div>
      <ul className="flex flex-col gap-3">
        {whatChanged.map((line, i) => (
          <motion.li
            key={i}
            className="flex items-start gap-3 sc-body"
            style={{ fontSize: "0.98rem", color: "var(--sc-text-2)" }}
            initial={{ opacity: 0, x: -8 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.6 }}
            transition={reduce ? { duration: 0 } : { duration: 0.4, ease: EASE_OUT_EXPO, delay: i * 0.08 }}
          >
            <span
              aria-hidden
              className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full"
              style={{
                background: inactive ? "var(--sc-text-3)" : "var(--sc-accent)",
                boxShadow: inactive ? "none" : "0 0 6px var(--sc-accent-glow)",
              }}
            />
            {line}
          </motion.li>
        ))}
      </ul>
    </section>
  );
}
