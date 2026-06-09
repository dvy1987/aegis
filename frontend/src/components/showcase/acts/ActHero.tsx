"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { EASE_OUT_EXPO } from "@/lib/motion";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { IgniteButton } from "@/components/showcase/fx/IgniteButton";
import { LivingGlyph } from "@/components/showcase/fx/LivingGlyph";
import { RiveOrFallback } from "@/components/showcase/fx/RiveOrFallback";

const HEADLINE = ["Watch", "a", "system", "teach", "itself."];

const TELEMETRY = [
  "SESSION 0x… · STAGE measure_before · 14/20",
  "JUDGE J3 grounding 0.62 → 0.81",
  "PHOENIX trace ingested · 312 spans",
  "GEPA candidate proposed · awaiting approval",
  "HOLD-OUT composite 0.40 → 0.75 (target)",
];

function scrollToInstrument() {
  if (typeof document === "undefined") return;
  document.getElementById("instrument")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function ActHero() {
  const reduce = useReducedMotion();
  const [glyphState, setGlyphState] = useState<"ignite" | "idle">(reduce ? "idle" : "ignite");

  useEffect(() => {
    if (reduce) return;
    const t = window.setTimeout(() => setGlyphState("idle"), 1700);
    return () => window.clearTimeout(t);
  }, [reduce]);

  return (
    <section
      id="hero"
      className="relative mx-auto flex min-h-dvh w-full flex-col justify-center px-6 py-24 md:px-12"
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="flex flex-col gap-6">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE_OUT_EXPO }}
          >
            <MonoLabel>AEGIS · SELF-IMPROVING APPEAL ENGINE</MonoLabel>
          </motion.div>

          <h1 className="sc-display" style={{ maxWidth: "16ch" }}>
            {HEADLINE.map((word, i) => (
              <motion.span
                key={i}
                className="inline-block"
                style={{ marginRight: "0.25em" }}
                initial={reduce ? false : { opacity: 0, y: 16, filter: "blur(8px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: 0.7, ease: EASE_OUT_EXPO, delay: 0.2 + i * 0.07 }}
              >
                {word}
              </motion.span>
            ))}
          </h1>

          <motion.p
            className="max-w-prose sc-body"
            style={{ fontSize: "1.15rem" }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.7 }}
          >
            Aegis drafts insurance-denial appeals, grades its own work against a held-out benchmark,
            and rewrites its own playbook from what it learns. No hand-tuning. Below, it does it live.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.9 }}
          >
            <IgniteButton variant="primary" onClick={scrollToInstrument}>
              Begin a live run
            </IgniteButton>
          </motion.div>
        </div>

        <div className="order-first lg:order-last">
          <RiveOrFallback fallback={<LivingGlyph state={glyphState} className="mx-auto" />} />
        </div>
      </div>

      <TelemetryStrip />
    </section>
  );
}

function TelemetryStrip() {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  useEffect(() => {
    if (reduce) return;
    const t = window.setInterval(() => setI((n) => (n + 1) % TELEMETRY.length), 2600);
    return () => window.clearInterval(t);
  }, [reduce]);

  return (
    <div className="mt-16 flex items-center gap-3" aria-hidden>
      <span className="h-1.5 w-1.5 rounded-full sc-pulse-soft" style={{ background: "var(--sc-accent)" }} />
      <motion.span
        key={i}
        initial={reduce ? false : { opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="sc-mono"
      >
        {TELEMETRY[i]}
      </motion.span>
      <span className="sc-mono sc-blink">▌</span>
    </div>
  );
}
