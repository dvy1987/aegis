"use client";
import type { MirrorBlock } from "@/lib/types";
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
  onContinue,
}: {
  mirror: MirrorBlock;
  onContinue: () => void;
}) {
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

      <Callout tone="sage" label="The strongest angle we see">
        {mirror.strongest_angle}
      </Callout>

      <div>
        <Button onClick={onContinue}>See the draft</Button>
      </div>
    </div>
  );
}
