"use client";
import type { AppealFixture } from "@/lib/types";
import { Button } from "@/components/Button";
import { Callout } from "@/components/ui/Callout";
import { Disclaimer } from "@/components/ui/Disclaimer";
import { ScoreMeter } from "@/components/ui/ScoreMeter";
import { StatusDot } from "@/components/ui/StatusDot";

function RailSection({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="flex flex-col gap-2">
      <p className="font-body text-sm text-text-secondary">{title}</p>
      <ul className="flex flex-col gap-1.5">
        {items.map((it, n) => (
          <li key={n} className="font-body text-sm text-text-tertiary">
            {it}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DraftEditor({
  result,
  onEdit,
  onContinue,
}: {
  result: AppealFixture;
  onEdit: (letter: string) => void;
  onContinue: () => void;
}) {
  const { outcome } = result;
  const approved = outcome.verdict === "APPROVE";

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="font-display text-display-md font-semibold tracking-tight">Your draft.</h2>
        <p className="mt-4 max-w-prose font-body text-lg text-text-secondary">
          Read every line. Change anything that doesn&apos;t sound like you — this is your letter.
        </p>
      </div>

      <div className="grid grid-cols-12 gap-8">
        <div className="col-span-12 lg:col-span-8">
          <label htmlFor="draft-letter" className="sr-only">
            Appeal letter
          </label>
          <textarea
            id="draft-letter"
            value={result.appeal_letter}
            onChange={(e) => onEdit(e.target.value)}
            className="min-h-[28rem] w-full rounded-md border border-border-default bg-surface-secondary p-6 font-body text-base leading-base text-text-primary focus-visible:outline-2 focus-visible:outline-accent-sage"
          />
        </div>

        <aside className="col-span-12 flex flex-col gap-6 lg:col-span-4">
          <div className="flex flex-col gap-2">
            <p className="inline-flex items-center gap-2 font-body text-sm text-text-secondary">
              <StatusDot tone={approved ? "sage" : "clay"} />
              {approved ? "Likely to clear the proxy review" : "May not clear the proxy review yet"}
            </p>
            <ScoreMeter score={outcome.score} threshold={outcome.threshold} />
            <p className="font-body text-sm text-text-tertiary">
              A transparent rule-based proxy — not a prediction of what your insurer will do.
            </p>
          </div>

          <RailSection title="What would make this stronger" items={outcome.gaps} />
          <RailSection
            title="Sources referenced"
            items={result.citations_used.map((c) => `${c.title}: ${c.quote}`)}
          />
          <RailSection title="Evidence still worth gathering" items={result.missing_evidence_checklist} />

          {result.risk_flags.length > 0 && (
            <Callout tone="clay" label="Worth knowing">
              {result.risk_flags.join(" ")}
            </Callout>
          )}

          <Disclaimer />
        </aside>
      </div>

      <div>
        <Button onClick={onContinue}>I&apos;m ready to decide</Button>
      </div>
    </div>
  );
}
