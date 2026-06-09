"use client";

import type { ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { EASE_OUT_EXPO } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { AccentLine } from "@/components/showcase/primitives/AccentLine";
import { MetricCounter } from "@/components/showcase/primitives/MetricCounter";
import { LivingGlyph } from "@/components/showcase/fx/LivingGlyph";
import { RiveOrFallback } from "@/components/showcase/fx/RiveOrFallback";
import { IgniteButton } from "@/components/showcase/fx/IgniteButton";

function replay() {
  if (typeof document === "undefined") return;
  document.getElementById("instrument")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function ActImpact() {
  const reduce = useReducedMotion();
  return (
    <section
      id="impact"
      className="relative mx-auto flex min-h-dvh w-full flex-col justify-center gap-14 px-6 py-24 md:px-12"
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.2fr_0.8fr]">
        <motion.div
          className="flex flex-col gap-6"
          initial={{ opacity: 0, y: 16, filter: "blur(8px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, amount: 0.5 }}
          transition={{ duration: 0.7, ease: EASE_OUT_EXPO }}
        >
          <MonoLabel>Why this matters</MonoLabel>
          <h2 className="sc-display" style={{ fontSize: "clamp(2.2rem, 4.5vw, 3.6rem)", maxWidth: "18ch" }}>
            99% of denied claims are never appealed. Aegis keeps getting better at the fight.
          </h2>
        </motion.div>

        <div>
          <RiveOrFallback fallback={<LivingGlyph state="settled" parallax={false} className="mx-auto" />} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <Metric label="Benchmark quality · target">
          <span className="sc-mono" style={{ fontSize: "1.6rem", color: "var(--sc-text-3)" }}>
            0.40&nbsp;→&nbsp;
          </span>
          <MetricCounter
            to={0.75}
            from={0.4}
            decimals={2}
            delay={0.2}
            className="sc-c-accent"
            style={{ fontSize: "1.6rem", fontWeight: 600, letterSpacing: "0" }}
          />
        </Metric>
        <Metric label="Judge dimensions">
          <MetricCounter
            to={7}
            delay={0.4}
            className="sc-c1"
            style={{ fontSize: "1.6rem", fontWeight: 600, letterSpacing: "0" }}
          />
        </Metric>
        <Metric label="Human-approved">
          <motion.span
            className="sc-c1"
            style={{ fontFamily: "var(--font-mono)", fontSize: "1.6rem", fontWeight: 600 }}
            initial={reduce ? false : { opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.6 }}
          >
            ALWAYS
          </motion.span>
        </Metric>
      </div>

      <div className="flex flex-col gap-6">
        <AccentLine />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <MonoLabel style={{ letterSpacing: "0.06em" }}>
            AEGIS · built on Google ADK + Gemini · observability by Arize Phoenix
          </MonoLabel>
          <IgniteButton variant="ghost" onClick={replay}>
            Replay the run
          </IgniteButton>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <MonoLabel>{label}</MonoLabel>
      <div className="flex items-baseline">{children}</div>
    </div>
  );
}
