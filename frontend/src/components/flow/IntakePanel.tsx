"use client";
import { useState } from "react";
import type { AppealRequest, CaseSummary, InsurerPin, PatientGender } from "@/lib/types";
import { Button } from "@/components/Button";
import { TextArea } from "@/components/ui/TextArea";
import { StatusDot } from "@/components/ui/StatusDot";
import { cn } from "@/lib/cn";

const INSURERS: InsurerPin[] = ["Aetna", "Cigna", "UHC"];

const GENDER_OPTIONS: { value: PatientGender; label: string }[] = [
  { value: "F", label: "Female" },
  { value: "M", label: "Male" },
  { value: "X", label: "Non-binary" },
];

export function IntakePanel({
  cases,
  onSubmit,
}: {
  cases: CaseSummary[];
  onSubmit: (req: AppealRequest) => void;
}) {
  const [denial, setDenial] = useState("");
  const [caseId, setCaseId] = useState("interactive_case");
  const [insurer, setInsurer] = useState<InsurerPin | "">("");
  const [patientAge, setPatientAge] = useState("");
  const [patientGender, setPatientGender] = useState<PatientGender | "">("");
  const [clinical, setClinical] = useState("");

  function pickSample(c: CaseSummary) {
    setDenial(c.denial_letter_text);
    setCaseId(c.case_id);
    setInsurer(c.insurer);
    setPatientAge(String(c.patient_age));
    setPatientGender(c.patient_gender);
    setClinical(c.clinical_context ?? "");
  }

  const ageNum = Number.parseInt(patientAge, 10);
  const ageValid = Number.isFinite(ageNum) && ageNum >= 1 && ageNum <= 120;
  const canSubmit = Boolean(denial.trim() && insurer && ageValid && patientGender);

  function submit() {
    if (!canSubmit || !insurer || !patientGender) return;
    onSubmit({
      denial_text: denial,
      case_id: caseId,
      insurer,
      patient_age: ageNum,
      patient_gender: patientGender,
      clinical_context: clinical,
    });
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

      <fieldset className="flex flex-col gap-6 rounded-md border border-border-default p-6">
        <legend className="px-1 font-body text-sm font-medium text-text-primary">
          About the person this appeal is for
        </legend>
        <p className="font-body text-sm text-text-secondary">
          These details help tailor the draft. All three are required.
        </p>

        <div className="flex flex-col gap-2">
          <span className="font-body text-sm text-text-secondary">Health plan insurer</span>
          <div className="flex flex-wrap gap-2">
            {INSURERS.map((name) => {
              const active = insurer === name;
              return (
                <button
                  key={name}
                  type="button"
                  onClick={() => setInsurer(name)}
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
                  {name}
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <label htmlFor="patient_age" className="font-body text-sm text-text-secondary">
              Age
            </label>
            <input
              id="patient_age"
              name="patient_age"
              type="number"
              min={1}
              max={120}
              inputMode="numeric"
              value={patientAge}
              onChange={(e) => setPatientAge(e.target.value)}
              placeholder="e.g. 42"
              className={cn(
                "w-full rounded-md border border-border-default bg-surface-secondary px-4 py-3",
                "font-body text-base text-text-primary placeholder:text-text-muted",
                "focus-visible:outline-2 focus-visible:outline-accent-sage",
              )}
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="patient_gender" className="font-body text-sm text-text-secondary">
              Gender
            </label>
            <select
              id="patient_gender"
              name="patient_gender"
              value={patientGender}
              onChange={(e) => setPatientGender(e.target.value as PatientGender)}
              className={cn(
                "w-full rounded-md border border-border-default bg-surface-secondary px-4 py-3",
                "font-body text-base text-text-primary",
                "focus-visible:outline-2 focus-visible:outline-accent-sage",
              )}
            >
              <option value="" disabled>
                Select gender
              </option>
              {GENDER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </fieldset>

      <TextArea
        label="Anything your doctor said or wrote"
        name="clinical_context"
        hint="Optional. A note, a diagnosis, a reason the treatment matters."
        value={clinical}
        onChange={(e) => setClinical(e.target.value)}
        className="min-h-28"
      />

      <div>
        <Button onClick={submit} disabled={!canSubmit}>
          Draft the appeal
        </Button>
      </div>
    </div>
  );
}
