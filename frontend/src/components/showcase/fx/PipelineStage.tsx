"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { PIPELINE_NODES } from "@/components/showcase/copy";
import { PipelineIcon, type PipelineKind } from "@/components/showcase/fx/PipelineIcon";
import { EASE_OUT_EXPO } from "@/lib/motion";

const NODES: { kind: PipelineKind; label: string; callout: string }[] = [...PIPELINE_NODES];

/**
 * Six-stage learning pipeline — nodes light and connectors draw as `progress`
 * advances (0 → 1). Each stage's one-liner appears only while that box is lit.
 */
export function PipelineStage({ progress }: { progress: number }) {
  const reduce = useReducedMotion();
  const pos = progress * (NODES.length - 1);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        {NODES.map((node, i) => {
          const active = i <= pos + 0.5;
          const fill = Math.max(0, Math.min(1, pos - i));
          return (
            <div key={node.kind} className="flex flex-1 items-center gap-4 lg:flex-col lg:gap-3">
              <GlassPanel
                variant={active ? "active" : "default"}
                className="flex w-full flex-col items-center gap-3 p-4 text-center transition-all duration-300"
              >
                <PipelineIcon kind={node.kind} active={active} size={28} />
                <span
                  className="sc-mono"
                  style={{ color: active ? "var(--sc-text)" : "var(--sc-text-3)", letterSpacing: "0.04em" }}
                >
                  {node.label}
                </span>
              </GlassPanel>
              {i < NODES.length - 1 && (
                <span
                  className="relative hidden h-px flex-1 self-center lg:block"
                  style={{ background: "var(--sc-hairline)" }}
                >
                  <span
                    className="absolute inset-0 origin-left"
                    style={{
                      background: "var(--sc-accent)",
                      boxShadow: "0 0 8px var(--sc-accent-glow)",
                      transform: `scaleX(${fill})`,
                    }}
                  />
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div className="grid min-h-[4.5rem] grid-cols-1 gap-3 sm:grid-cols-2">
        <AnimatePresence mode="popLayout">
          {NODES.map((node, i) => {
            const active = i <= pos + 0.5;
            if (!active) return null;
            return (
              <motion.div
                key={node.kind}
                layout
                className="flex items-start gap-2"
                initial={reduce ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduce ? undefined : { opacity: 0, y: -6 }}
                transition={reduce ? { duration: 0 } : { duration: 0.45, ease: EASE_OUT_EXPO }}
              >
                <span
                  className="sc-mono"
                  style={{ color: "var(--sc-accent)", whiteSpace: "nowrap", fontSize: "0.9rem" }}
                >
                  {node.label} —
                </span>
                <span className="sc-body" style={{ fontSize: "1.05rem", color: "var(--sc-text-2)", lineHeight: 1.5 }}>
                  {node.callout}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
