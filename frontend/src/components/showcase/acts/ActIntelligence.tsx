"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView, useReducedMotion } from "framer-motion";
import { ActSection } from "@/components/showcase/primitives/ActSection";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { GlassPanel } from "@/components/showcase/primitives/GlassPanel";
import { CounterfactualCard } from "@/components/showcase/versus/CounterfactualCard";
import { PipelineIcon, type PipelineKind } from "@/components/showcase/fx/PipelineIcon";

const NODES: { kind: PipelineKind; label: string; callout?: string }[] = [
  { kind: "draft", label: "Draft" },
  {
    kind: "judge",
    label: "Judge panel",
    callout: "Seven-dimension panel: two hard safety gates + five weighted scores. Six run as ADK agents.",
  },
  {
    kind: "memory",
    label: "Phoenix memory",
    callout: "It reads its own past traces before drafting.",
  },
  { kind: "optimize", label: "GEPA optimizer" },
  { kind: "approve", label: "Human approval" },
  { kind: "promote", label: "Promote" },
];

export function ActIntelligence({
  on,
  off,
}: {
  on: number;
  off: number;
}) {
  return (
    <ActSection id="intelligence" className="flex flex-col gap-14">
      <div className="flex flex-col gap-2">
        <MonoLabel>The intelligence layer</MonoLabel>
        <h2 className="sc-h2">How it gets better.</h2>
        <p className="max-w-prose sc-body">
          Aegis grades every draft against a held-out benchmark, writes the result to its own memory,
          and an optimizer rewrites its playbook from the pattern of its past failures. A person
          approves before anything ships.
        </p>
      </div>

      <Pipeline />

      <CounterfactualCard on={on} off={off} />
    </ActSection>
  );
}

function Pipeline() {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.4 });
  const [rawStep, setRawStep] = useState(-1);

  useEffect(() => {
    if (!inView || reduce) return;
    let i = -1;
    const id = window.setInterval(() => {
      i += 1;
      setRawStep(i);
      if (i >= NODES.length - 1) window.clearInterval(id);
    }, 280);
    return () => window.clearInterval(id);
  }, [inView, reduce]);

  const step = reduce ? NODES.length : rawStep;

  return (
    <div ref={ref} className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch">
        {NODES.map((node, i) => {
          const active = i <= step;
          return (
            <div key={node.kind} className="flex flex-1 items-center gap-4 lg:flex-col lg:gap-3">
              <GlassPanel
                variant={active ? "active" : "default"}
                className="flex w-full flex-col items-center gap-3 p-4 text-center transition-all duration-500"
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
                  <motion.span
                    className="absolute inset-0 origin-left"
                    style={{ background: "var(--sc-accent)", boxShadow: "0 0 8px var(--sc-accent-glow)" }}
                    initial={{ scaleX: reduce ? 1 : 0 }}
                    animate={{ scaleX: i < step ? 1 : 0 }}
                    transition={{ duration: 0.3 }}
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
