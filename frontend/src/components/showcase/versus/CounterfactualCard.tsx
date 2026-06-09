"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import { BEAT_MS, useTheatrical } from "@/lib/motion";
import { Gauge } from "@/components/showcase/primitives/Gauge";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import {
  COUNTERFACTUAL_BODY,
  COUNTERFACTUAL_EYEBROW,
  COUNTERFACTUAL_FOOTNOTE,
  COUNTERFACTUAL_GAUGE_OFF,
  COUNTERFACTUAL_GAUGE_ON,
  COUNTERFACTUAL_HEADLINE,
  COUNTERFACTUAL_MEMORY_OFF,
  COUNTERFACTUAL_MEMORY_ON,
} from "@/components/showcase/copy";
import { MemoryToggle } from "@/components/showcase/fx/MemoryToggle";

/**
 * The killer counterfactual. A real toggle drives which composite is shown;
 * switching memory OFF visibly decays the panel (desaturate + retreat) — the
 * memory-on/off proof from the design doc Act V-b.
 */
export function CounterfactualCard({ on, off }: { on: number; off: number }) {
  const [memoryOn, setMemoryOn] = useState(true);
  const { runMoment } = useTheatrical();
  const value = memoryOn ? on : off;

  function handleMemoryChange(next: boolean) {
    setMemoryOn(next);
    if (!next) {
      runMoment("memory-decay", () => undefined, BEAT_MS);
    }
  }

  return (
    <GlassPanel
      data-theatrical-zone="memory-decay"
      className={cn("flex flex-col gap-5 p-6 transition-[filter]", !memoryOn && "sc-decayed")}
    >
      <div className="flex flex-col gap-1">
        <MonoLabel>{COUNTERFACTUAL_EYEBROW}</MonoLabel>
        <h3 className="sc-h2" style={{ fontSize: "1.6rem" }}>
          {COUNTERFACTUAL_HEADLINE}
        </h3>
        <p className="mt-1 max-w-prose sc-body" style={{ fontSize: "0.95rem", color: "var(--sc-text-2)" }}>
          {COUNTERFACTUAL_BODY}
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <MemoryToggle on={memoryOn} onChange={handleMemoryChange} />
        <motion.span
          key={memoryOn ? "on" : "off"}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="sc-mono"
          style={{ color: memoryOn ? "var(--sc-accent)" : "var(--sc-warn)" }}
        >
          {memoryOn ? COUNTERFACTUAL_MEMORY_ON : COUNTERFACTUAL_MEMORY_OFF}
        </motion.span>
      </div>

      <Gauge
        value={value}
        live
        label={memoryOn ? "Composite · memory on" : "Composite · memory off"}
        tone={memoryOn ? "accent" : "warn"}
      />

      <p className="sc-mono" style={{ color: "var(--sc-text-3)" }}>
        The memory-off figure is a design target where a measured run is not yet recorded.
      </p>
    </GlassPanel>
  );
}
