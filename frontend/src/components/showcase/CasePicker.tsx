"use client";
import type { CaseSummary } from "@/lib/types";
import { StatusDot } from "@/components/ui/StatusDot";
import { cn } from "@/lib/cn";

export function CasePicker({
  cases,
  selected,
  onSelect,
}: {
  cases: CaseSummary[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div role="radiogroup" aria-label="Choose a case" className="flex flex-wrap gap-2">
      {cases.map((c) => {
        const active = c.case_id === selected;
        return (
          <button
            key={c.case_id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onSelect(c.case_id)}
            className={cn(
              "inline-flex items-center gap-2 rounded-pill border px-4 py-2 font-body text-sm",
              "focus-visible:outline-2 focus-visible:outline-accent-sage",
              active
                ? "border-border-accent bg-accent-sage-tint text-text-primary"
                : "border-border-default text-text-secondary hover:border-border-strong",
            )}
          >
            {active && <StatusDot />}
            {c.insurer} · {c.denial_type}
          </button>
        );
      })}
    </div>
  );
}
