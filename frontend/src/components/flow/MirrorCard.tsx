"use client";
import { useState } from "react";
import type { MirrorBlock } from "@/lib/types";
import { AdditionalDetailsModal } from "@/components/flow/AdditionalDetailsModal";
import { Button } from "@/components/Button";
import { Callout } from "@/components/ui/Callout";

function Line({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="font-body text-sm text-text-tertiary">{label}</p>
      <p className="font-body text-base text-text-primary">{value}</p>
    </div>
  );
}

export function MirrorCard({
  mirror,
  additionalDetails = "",
  onSaveDetails,
  onSaveProgress,
  onContinue,
}: {
  mirror: MirrorBlock;
  additionalDetails?: string;
  onSaveDetails: (text: string) => void;
  onSaveProgress: () => boolean;
  onContinue: () => void;
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  function handleSaveProgress() {
    if (onSaveProgress()) {
      setSavedMessage("Saved on this device. You can close the page and come back later.");
    } else {
      setSavedMessage("Could not save on this device. Try again, or continue to the draft.");
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="font-display text-display-md font-semibold tracking-tight">
          Here&apos;s what we heard.
        </h2>
        <p className="mt-4 max-w-prose font-body text-lg text-text-secondary">
          Read this back to yourself. If it matches your situation, we&apos;ll turn it into a letter.
        </p>
      </div>

      <div className="flex flex-col gap-6">
        <Line label="Who denied it" value={mirror.insurer} />
        <Line label="What was denied" value={mirror.what_was_denied} />
        <Line label="Why they said no" value={mirror.why_they_said_no} />
        <Line label="Your deadline" value={mirror.deadline_note} />
      </div>

      {mirror.what_helps_note ? (
        <Callout tone="sage" label="What supports your appeal">
          <span className="whitespace-pre-line">{mirror.what_helps_note}</span>
        </Callout>
      ) : null}

      <Callout tone="clay" label="Worth gathering before you file">
        <span className="whitespace-pre-line">{mirror.gaps_note}</span>
      </Callout>

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <Button onClick={onContinue}>See the draft</Button>
        <Button type="button" variant="secondary" onClick={() => setModalOpen(true)}>
          Add more details
        </Button>
        <Button type="button" variant="ghost" onClick={handleSaveProgress}>
          Save for later
        </Button>
      </div>
      {additionalDetails ? (
        <p className="font-body text-sm text-text-tertiary">
          You added extra details — they&apos;ll show on the draft page for you to use.
        </p>
      ) : null}
      {savedMessage ? (
        <p className="font-body text-sm text-text-secondary">{savedMessage}</p>
      ) : null}

      <AdditionalDetailsModal
        open={modalOpen}
        initialValue={additionalDetails}
        onClose={() => setModalOpen(false)}
        onSave={onSaveDetails}
      />
    </div>
  );
}
