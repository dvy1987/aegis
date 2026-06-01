"use client";
import { useState } from "react";
import type { AppealRequest, CaseSummary } from "@/lib/types";
import { Button } from "@/components/Button";
import { TextArea } from "@/components/ui/TextArea";
import { StatusDot } from "@/components/ui/StatusDot";
import { cn } from "@/lib/cn";

export function IntakePanel({
  cases,
  onSubmit,
}: {
  cases: CaseSummary[];
  onSubmit: (req: AppealRequest) => void;
}) {
  const [denial, setDenial] = useState("");
  const [clinical, setClinical] = useState("");
  const [caseId, setCaseId] = useState("interactive_case");

  function pickSample(c: CaseSummary) {
    setDenial(c.denial_letter_text);
    setClinical(c.clinical_context);
    setCaseId(c.case_id);
  }

  function submit() {
    if (!denial.trim()) return;
    onSubmit({ denial_text: denial, clinical_context: clinical, case_id: caseId });
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-display-lg font-semibold tracking-tight">
          Tell us what happened.
        </h1>
        <p className="mt-4 max-w-prose font-body text-lg text-text-secondary">
          Paste the denial letter below. If you would rather start from an example, pick one of the
          sample cases. Plain English is fine — no jargon required.
        </p>
      </div>

      <TextArea
        label="Paste the denial letter"
        name="denial_text"
        value={denial}
        onChange={(e) => {
          setDenial(e.target.value);
          setCaseId("interactive_case");
        }}
        placeholder="Dear Member, We have reviewed your request for..."
      />

      <div className="flex flex-col gap-3">
        <p className="font-body text-sm text-text-secondary">Or start from a sample case</p>
        <div className="flex flex-wrap gap-2">
          {cases.map((c) => {
            const active = c.case_id === caseId;
            return (
              <button
                key={c.case_id}
                type="button"
                onClick={() => pickSample(c)}
                aria-pressed={active}
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
      </div>

      <TextArea
        label="Anything your doctor said or wrote"
        name="clinical_context"
        hint="Optional. A note, a diagnosis, a reason the treatment matters."
        value={clinical}
        onChange={(e) => setClinical(e.target.value)}
        className="min-h-28"
      />

      <div>
        <Button onClick={submit} disabled={!denial.trim()}>
          Draft the appeal
        </Button>
      </div>
    </div>
  );
}
