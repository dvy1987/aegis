"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { EASE_OUT_EXPO } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { AccentLine } from "@/components/showcase/primitives/AccentLine";

/**
 * The thesis beat. Uses CSS `position: sticky` for a robust "pin" on ≥lg (no
 * GSAP dependency); content resolves on scroll into view. 90% negative space.
 */
export function ActThesis() {
  const reduce = useReducedMotion();
  return (
    <section id="thesis" className="lg:min-h-[150vh]">
      <div className="sticky top-0 flex min-h-dvh items-center">
        <div
          className="mx-auto flex w-full flex-col gap-12 px-6 md:px-12"
          style={{ maxWidth: "var(--sc-container-max)" }}
        >
          <motion.div
            className="flex max-w-3xl flex-col gap-5"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.5 }}
          >
            <motion.h2
              className="sc-serif"
              style={{ fontSize: "clamp(1.9rem, 4vw, 3rem)", fontWeight: 600, color: "var(--sc-text)", lineHeight: 1.15 }}
              variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0 } }}
              transition={{ duration: 0.7, ease: EASE_OUT_EXPO }}
            >
              Most AI agents never improve. They answer the same way on day one and day one thousand.
            </motion.h2>
            <motion.p
              className="sc-serif"
              style={{ fontSize: "clamp(1.4rem, 3vw, 2.1rem)", color: "var(--sc-accent)", lineHeight: 1.2 }}
              variants={{ hidden: { opacity: 0, y: 16 }, visible: { opacity: 1, y: 0 } }}
              transition={{ duration: 0.7, ease: EASE_OUT_EXPO, delay: 0.15 }}
            >
              Aegis reads its own past evaluations before it drafts — and gets measurably better.
            </motion.p>
          </motion.div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 sm:gap-12">
            <ThesisNode
              label="Static-prompt agents"
              inert
              caption="One prompt. Frozen at launch."
            />
            <ThesisNode
              label="Aegis"
              caption="Reads its traces. Rewrites its playbook."
            >
              <div className="mt-3 flex flex-col gap-1.5">
                <AccentLine className="w-24" />
                <span className="sc-serif" style={{ color: "var(--sc-accent)", fontSize: "1.1rem" }}>
                  learns
                </span>
              </div>
            </ThesisNode>
          </div>

          <motion.div
            initial={reduce ? false : { opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <MonoLabel style={{ textTransform: "none", letterSpacing: "0.04em", color: "var(--sc-text-3)" }}>
              THESIS — if turning memory off doesn&apos;t degrade quality, the idea has failed. So we
              turn it off later and show you.
            </MonoLabel>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function ThesisNode({
  label,
  caption,
  inert = false,
  children,
}: {
  label: string;
  caption: string;
  inert?: boolean;
  children?: ReactNode;
}) {
  const reduce = useReducedMotion();
  const color = inert ? "var(--sc-text-3)" : "var(--sc-accent)";
  return (
    <motion.div
      className="flex items-start gap-4"
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.6 }}
      transition={{ duration: 0.6, ease: EASE_OUT_EXPO, delay: inert ? 0.1 : 0.25 }}
    >
      <span
        className={inert || reduce ? "" : "sc-breath"}
        style={{
          display: "inline-block",
          width: 14,
          height: 14,
          borderRadius: 999,
          marginTop: 6,
          background: inert ? "transparent" : color,
          border: `1.5px solid ${color}`,
          boxShadow: inert ? "none" : "0 0 14px var(--sc-accent-glow)",
        }}
      />
      <div className="flex flex-col">
        <span className="sc-serif" style={{ fontSize: "1.3rem", color: inert ? "var(--sc-text-2)" : "var(--sc-text)" }}>
          {label}
        </span>
        <span className="sc-mono" style={{ marginTop: 4 }}>
          {caption}
        </span>
        {children}
      </div>
    </motion.div>
  );
}
