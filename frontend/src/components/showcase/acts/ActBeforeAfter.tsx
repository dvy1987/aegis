"use client";

import type { CaseSummary, ShowcaseBundle } from "@/lib/types";
import { ActSection } from "@/components/showcase/primitives/ActSection";
import { MonoLabel } from "@/components/showcase/primitives/MonoLabel";
import { CaseCycler } from "@/components/showcase/versus/CaseCycler";
import { VersusPanel } from "@/components/showcase/versus/VersusPanel";
import { DiffCard } from "@/components/showcase/versus/DiffCard";

/** Act IV — the money shot. Case cycling replaces the old pill row. */
export function ActBeforeAfter({
  bundle,
  cases,
  selected,
  onSelect,
}: {
  bundle: ShowcaseBundle | null;
  cases: CaseSummary[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <ActSection id="before-after" className="flex flex-col gap-10">
      <div className="flex flex-col gap-2">
        <MonoLabel>Before / after</MonoLabel>
        <h2 className="sc-h2">The same denial. Before and after it learned.</h2>
      </div>

      <CaseCycler cases={cases} selected={selected} onSelect={onSelect} />

      {bundle && (
        <>
          <VersusPanel key={`versus-${bundle.case_id}`} bundle={bundle} />
          <DiffCard key={`diff-${bundle.case_id}`} whatChanged={bundle.what_changed} />
        </>
      )}
    </ActSection>
  );
}
