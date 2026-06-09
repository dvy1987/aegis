"use client";

import { motion, useReducedMotion } from "framer-motion";
import { EASE_OUT_EXPO } from "@/lib/motion";
import {
  GEPA_PILLARS,
  GEPA_SPOTLIGHT_BODY,
  GEPA_SPOTLIGHT_EYEBROW,
  GEPA_SPOTLIGHT_FOOTNOTE,
  GEPA_SPOTLIGHT_HEADLINE,
} from "@/components/showcase/copy";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";

/**
 * Presentation beat — names GEPA before the self-drawing pipeline so judges
 * hear the talking point even if they never start a live run.
 */
export function GepaSpotlight() {
  const reduce = useReducedMotion();

  return (
    <motion.div
      className="flex flex-col gap-8"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.35 }}
      transition={reduce ? { duration: 0 } : { duration: 0.7, ease: EASE_OUT_EXPO }}
    >
      <GlassPanel variant="glass" className="flex flex-col gap-6 p-6 md:p-8">
        <div className="flex flex-col gap-3">
          <MonoLabel>{GEPA_SPOTLIGHT_EYEBROW}</MonoLabel>
          <h3 className="sc-h2" style={{ fontSize: "clamp(1.5rem, 3vw, 2rem)", maxWidth: "22ch" }}>
            {GEPA_SPOTLIGHT_HEADLINE}
          </h3>
          <p className="max-w-prose sc-body" style={{ color: "var(--sc-text-2)" }}>
            {GEPA_SPOTLIGHT_BODY}
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {GEPA_PILLARS.map((pillar, i) => (
            <motion.div
              key={pillar.title}
              className="sc-panel-sunken flex flex-col gap-2 rounded-md p-4"
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.5 }}
              transition={
                reduce ? { duration: 0 } : { duration: 0.45, ease: EASE_OUT_EXPO, delay: i * 0.07 }
              }
            >
              <span className="sc-mono" style={{ color: "var(--sc-accent)", letterSpacing: "0.06em" }}>
                {pillar.title}
              </span>
              <p className="sc-body" style={{ fontSize: "0.92rem", color: "var(--sc-text-2)", lineHeight: 1.5 }}>
                {pillar.body}
              </p>
            </motion.div>
          ))}
        </div>

        <MonoLabel style={{ color: "var(--sc-text-3)", letterSpacing: "0.1em" }}>
          {GEPA_SPOTLIGHT_FOOTNOTE}
        </MonoLabel>
      </GlassPanel>
    </motion.div>
  );
}
