"use client";
import type { ShowcaseBundle } from "@/lib/types";
import { ScoreMeter } from "@/components/ui/ScoreMeter";
import { StatusDot } from "@/components/ui/StatusDot";
import { Callout } from "@/components/ui/Callout";

function Column({
  title,
  composite,
  verdict,
  excerpt,
}: {
  title: string;
  composite: number;
  verdict: "APPROVE" | "DENY";
  excerpt: string;
}) {
  return (
    <div className="col-span-12 flex flex-col gap-4 md:col-span-6">
      <p className="font-body text-sm text-text-tertiary">{title}</p>
      <ScoreMeter score={composite} label="Composite quality" />
      <p className="inline-flex items-center gap-2 font-body text-sm text-text-secondary">
        <StatusDot tone={verdict === "APPROVE" ? "sage" : "clay"} />
        Simulator verdict: {verdict}
      </p>
      <p className="rounded-md border border-border-subtle bg-surface-secondary p-4 font-body text-sm leading-base text-text-secondary">
        {excerpt}
      </p>
    </div>
  );
}

export function VersusPanel({ bundle }: { bundle: ShowcaseBundle }) {
  return (
    <section className="flex flex-col gap-6">
      <h2 className="font-display text-display-md font-semibold tracking-tight">
        The same case, before and after learning.
      </h2>
      <div className="grid grid-cols-12 gap-8">
        <Column title="Earlier draft" composite={bundle.v1.composite} verdict={bundle.v1.verdict} excerpt={bundle.v1.letter_excerpt} />
        <Column title="Improved draft" composite={bundle.v3.composite} verdict={bundle.v3.verdict} excerpt={bundle.v3.letter_excerpt} />
      </div>
      <p className="font-body text-base text-text-secondary">
        Measured lift on held-out cases:{" "}
        <span className="font-mono text-text-primary">+{bundle.lift_relative_pct.toFixed(1)}%</span>
      </p>
      {!bundle.measured && (
        <Callout tone="neutral" label="Note">
          Illustrative for this case. Measured numbers are shown for the cases that have a recorded
          run.
        </Callout>
      )}
    </section>
  );
}
