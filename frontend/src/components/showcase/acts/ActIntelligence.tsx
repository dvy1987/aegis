"use client";

import { useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { ScrollTrigger, useGsapContext } from "@/lib/motion";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { CounterfactualCard } from "@/components/showcase/versus/CounterfactualCard";
import { PIPELINE_NODES } from "@/components/showcase/copy";
import { PipelineIcon, type PipelineKind } from "@/components/showcase/fx/PipelineIcon";

const NODES: { kind: PipelineKind; label: string; callout?: string }[] = [...PIPELINE_NODES];

export function ActIntelligence({ on, off }: { on: number; off: number }) {
  return (
    <section
      id="intelligence"
      className="mx-auto flex w-full flex-col gap-14 px-6 py-24 md:px-12 md:py-32"
      style={{ maxWidth: "var(--sc-container-max)" }}
    >
      <Pipeline />

      <CounterfactualCard on={on} off={off} />
    </section>
  );
}

function Pipeline() {
  const reduce = useReducedMotion();
  const root = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(0);

  // Scroll-scrubbed self-draw: connectors grow and nodes light as the section
  // passes through the viewport. Reduced-motion shows the fully-drawn end state.
  useGsapContext(
    () => {
      ScrollTrigger.create({
        trigger: root.current,
        start: "top 72%",
        end: "bottom 58%",
        scrub: 0.5,
        onUpdate: (self) => setProgress(self.progress),
      });
    },
    { scope: root },
  );

  const shown = reduce ? 1 : progress;
  const pos = shown * (NODES.length - 1); // 0 → n-1

  return (
    <div ref={root} className="flex flex-col gap-6">
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
                <span className="relative hidden h-px flex-1 self-center lg:block" style={{ background: "var(--sc-hairline)" }}>
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

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {NODES.filter((n) => n.callout).map((n) => (
          <div key={n.kind} className="flex items-start gap-2">
            <span className="sc-mono" style={{ color: "var(--sc-accent)", whiteSpace: "nowrap" }}>
              {n.label} —
            </span>
            <span className="sc-body" style={{ fontSize: "0.9rem", color: "var(--sc-text-2)" }}>
              {n.callout}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
