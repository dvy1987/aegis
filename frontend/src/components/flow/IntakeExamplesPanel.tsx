"use client";

import { useId, useState } from "react";
import type { CaseSummary } from "@/lib/types";
import { ChevronDownIcon } from "@/icons";
import { cn } from "@/lib/cn";

export function IntakeExamplesPanel({
  cases,
  selectedCaseId,
  onSelect,
}: {
  cases: CaseSummary[];
  selectedCaseId: string | null;
  onSelect: (summary: CaseSummary) => void;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  if (!cases.length) return null;

  return (
    <div className="rounded-md border border-border-subtle bg-surface-tertiary/50">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex w-full items-center justify-between gap-3 px-4 py-3 text-left",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-sage",
        )}
      >
        <span className="font-body text-sm font-medium text-text-secondary">Examples</span>
        <ChevronDownIcon
          size={16}
          className={cn(
            "shrink-0 text-text-muted transition-transform duration-[var(--motion-duration-base)] ease-[var(--motion-ease-soft)]",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <div id={panelId} className="border-t border-border-subtle px-3 py-3">
          <p className="px-1 pb-3 font-body text-xs leading-snug text-text-tertiary">
            Some example denial letters to help you understand.
          </p>
          <ul className="flex flex-col gap-1">
            {cases.map((c) => {
              const active = selectedCaseId === c.case_id;
              return (
                <li key={c.case_id}>
                  <button
                    type="button"
                    onClick={() => {
                      onSelect(c);
                      setOpen(false);
                    }}
                    aria-pressed={active}
                    className={cn(
                      "w-full rounded-sm px-2 py-2 text-left",
                      "focus-visible:outline-2 focus-visible:outline-accent-sage",
                      active
                        ? "bg-accent-sage-tint"
                        : "hover:bg-surface-secondary/80",
                    )}
                  >
                    <span className="block font-body text-xs font-medium text-text-secondary">
                      {c.insurer} · {c.denial_type}
                    </span>
                    <span className="mt-0.5 block font-body text-xs leading-snug text-text-tertiary line-clamp-2">
                      {c.headline}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
