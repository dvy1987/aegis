"use client";
import type { AppealFixture } from "@/lib/types";
import { Button } from "@/components/Button";
import { Disclaimer } from "@/components/ui/Disclaimer";

export function DraftEditor({
  result,
  additionalDetails,
  onEdit,
  onContinue,
}: {
  result: AppealFixture;
  additionalDetails?: string;
  onEdit: (letter: string) => void;
  onContinue: () => void;
}) {
  return (
    <div className="flex min-h-[calc(100dvh-12rem)] flex-col gap-8">
      <div>
        <h2 className="font-display text-display-md font-semibold tracking-tight">Your draft.</h2>
        <p className="mt-4 max-w-prose font-body text-lg text-text-secondary">
          Read every line. Change anything that doesn&apos;t sound like you — this is your letter.
        </p>
      </div>

      {additionalDetails ? (
        <div className="rounded-md border border-border-subtle bg-surface-tertiary/60 px-5 py-4">
          <p className="font-body text-sm font-medium text-text-secondary">Details you added</p>
          <p className="mt-2 font-body text-sm whitespace-pre-line text-text-tertiary">
            {additionalDetails}
          </p>
        </div>
      ) : null}

      <div className="flex min-h-0 flex-1 flex-col">
        <label htmlFor="draft-letter" className="sr-only">
          Appeal letter
        </label>
        <textarea
          id="draft-letter"
          value={result.appeal_letter}
          onChange={(e) => onEdit(e.target.value)}
          className="min-h-[min(72dvh,52rem)] w-full flex-1 resize-y rounded-md border border-border-default bg-surface-secondary p-6 font-body text-base leading-relaxed text-text-primary focus-visible:outline-2 focus-visible:outline-accent-sage md:p-8 md:text-[1.0625rem]"
        />
      </div>

      <Disclaimer />

      <div>
        <Button onClick={onContinue}>I&apos;m ready to decide</Button>
      </div>
    </div>
  );
}
