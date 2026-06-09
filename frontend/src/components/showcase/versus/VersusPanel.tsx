"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { ShowcaseBundle, Verdict } from "@/lib/types";
import { EASE_OUT_EXPO } from "@/lib/motion";
import { cn } from "@/lib/cn";
import { Gauge } from "@/components/showcase/primitives/Gauge";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { LiftGauge } from "@/components/showcase/fx/LiftGauge";
import { ArrowUpRightIcon } from "@/icons";

/** The page's one symmetric moment — v1 vs v3, with the lift in the middle. */
export function VersusPanel({ bundle }: { bundle: ShowcaseBundle }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 items-stretch gap-5 lg:grid-cols-[1fr_auto_1fr]">
        <DraftColumn
          side="before"
          title="Earlier draft"
          version="v1"
          composite={bundle.v1.composite}
          verdict={bundle.v1.verdict}
          excerpt={bundle.v1.letter_excerpt}
        />

        <div className="flex flex-col items-center justify-center gap-2 px-2 py-4">
          <MonoLabel>Measured lift · held-out</MonoLabel>
          <LiftGauge value={bundle.lift_relative_pct} />
        </div>

        <DraftColumn
          side="after"
          title="Improved draft"
          version="v3"
          composite={bundle.v3.composite}
          verdict={bundle.v3.verdict}
          excerpt={bundle.v3.letter_excerpt}
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        {!bundle.measured && (
          <p className="sc-mono" style={{ color: "var(--sc-text-3)" }}>
            Illustrative for this case. Measured numbers shown where a run is recorded.
          </p>
        )}
        {bundle.phoenix_url && (
          <a
            href={bundle.phoenix_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 sc-mono transition-colors hover:opacity-80"
            style={{ color: "var(--sc-accent)" }}
          >
            INSPECT THE UNDERLYING TRACE
            <ArrowUpRightIcon size={16} />
          </a>
        )}
      </div>
    </div>
  );
}

function DraftColumn({
  side,
  title,
  version,
  composite,
  verdict,
  excerpt,
}: {
  side: "before" | "after";
  title: string;
  version: string;
  composite: number;
  verdict: Verdict;
  excerpt: string;
}) {
  const improved = side === "after";
  return (
    <GlassPanel variant={improved ? "active" : "default"} className="flex flex-col gap-4 p-6">
      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-col">
          <MonoLabel>{version}</MonoLabel>
          <span className="sc-serif" style={{ color: "var(--sc-text)", fontSize: "1.15rem" }}>
            {title}
          </span>
        </div>
        <VerdictLamp verdict={verdict} bloom={improved} />
      </div>
      <Gauge value={composite} label="Composite quality" tone={improved ? "accent" : "deny"} />
      <p
        className="sc-body rounded-md p-4"
        style={{
          fontSize: "0.9rem",
          color: "var(--sc-text-2)",
          background: "var(--sc-bg-sunken)",
          border: "1px solid var(--sc-hairline)",
        }}
      >
        {excerpt}
      </p>
    </GlassPanel>
  );
}

function VerdictLamp({ verdict, bloom }: { verdict: Verdict; bloom?: boolean }) {
  const reduce = useReducedMotion();
  const approve = verdict === "APPROVE";
  const color = approve ? "var(--sc-accent)" : "var(--sc-deny)";
  return (
    <motion.span
      className={cn("inline-flex items-center gap-2 rounded-full px-3 py-1")}
      style={{ border: `1px solid ${color}`, color }}
      initial={bloom && !reduce ? { boxShadow: "0 0 0 transparent" } : false}
      whileInView={bloom && !reduce ? { boxShadow: ["0 0 0 transparent", "0 0 24px var(--sc-accent-glow)", "0 0 12px var(--sc-accent-glow)"] } : undefined}
      viewport={{ once: true, amount: 0.8 }}
      transition={{ duration: 1.1, ease: EASE_OUT_EXPO }}
    >
      <span className="h-2 w-2 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
      <span className="sc-mono" style={{ color }}>
        {approve ? "SIMULATOR · APPROVE" : "SIMULATOR · DENY"}
      </span>
    </motion.span>
  );
}
