"use client";

import { Button } from "@/components/Button";
import { formatSavedAt } from "@/lib/flow/persistAppealSession";

export function ResumeAppealBanner({
  savedAt,
  stepLabel,
  onResume,
  onDismiss,
}: {
  savedAt: string;
  stepLabel: string;
  onResume: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="mb-8 rounded-md border border-border-default bg-surface-secondary p-5">
      <p className="font-body text-base text-text-primary">
        You have a saved appeal on this device ({stepLabel}, saved {formatSavedAt(savedAt)}).
      </p>
      <p className="mt-2 font-body text-sm text-text-secondary">
        Resume where you left off, or start fresh.
      </p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row">
        <Button type="button" onClick={onResume}>
          Resume saved appeal
        </Button>
        <Button type="button" variant="ghost" onClick={onDismiss}>
          Start fresh
        </Button>
      </div>
    </div>
  );
}
