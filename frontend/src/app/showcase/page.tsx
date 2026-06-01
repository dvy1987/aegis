"use client";
import { useEffect, useState } from "react";
import { getDataSource } from "@/lib/data";
import type { CaseSummary, ShowcaseBundle } from "@/lib/types";
import { Nav } from "@/components/Nav";
import { CasePicker } from "@/components/showcase/CasePicker";
import { VersusPanel } from "@/components/showcase/VersusPanel";
import { DiffCard } from "@/components/showcase/DiffCard";
import { CounterfactualCard } from "@/components/showcase/CounterfactualCard";
import { ArrowUpRightIcon } from "@/icons";

const DEFAULT_CASE = "test_case_03_cigna_mednec";

export default function ShowcasePage() {
  const ds = getDataSource();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [sel, setSel] = useState(DEFAULT_CASE);
  const [bundle, setBundle] = useState<ShowcaseBundle | null>(null);

  useEffect(() => {
    ds.listCases().then(setCases);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    ds.getShowcase(sel).then(setBundle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel]);

  return (
    <div className="flex min-h-dvh flex-col bg-surface-primary text-text-primary">
      <Nav />
      <main className="mx-auto flex w-full max-w-(--container-app) flex-1 flex-col gap-16 px-6 py-16 md:px-12 md:py-24">
        <header className="flex flex-col gap-4">
          <p className="inline-flex items-center gap-2 font-body text-sm text-text-secondary">
            <span aria-hidden className="signature-dot" />
            How Aegis learns
          </p>
          <h1 className="max-w-3xl font-display text-display-lg font-semibold leading-[1.1] tracking-tight md:text-display-xl">
            This tool improves from its own observability.
          </h1>
          <p className="max-w-prose font-body text-lg text-text-secondary">
            Pick a case. The same denial is drafted by an earlier version and an improved one, scored
            on a held-out benchmark. The improvement comes from the system reading its own past
            evaluations — not from hand-tuning.
          </p>
        </header>

        <CasePicker cases={cases} selected={sel} onSelect={setSel} />

        {bundle && (
          <>
            <VersusPanel bundle={bundle} />
            <DiffCard whatChanged={bundle.what_changed} />
            <CounterfactualCard on={bundle.counterfactual.on_composite} off={bundle.counterfactual.off_composite} />
            {bundle.phoenix_url && (
              <a
                href={bundle.phoenix_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 font-body text-base text-text-link hover:text-text-primary"
              >
                Open the underlying trace
                <ArrowUpRightIcon size={16} />
              </a>
            )}
          </>
        )}
      </main>
    </div>
  );
}
