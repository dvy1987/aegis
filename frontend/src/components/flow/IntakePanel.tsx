"use client";
import { useState } from "react";
import type { AppealRequest, CaseSummary, InsurerPin, PatientGender } from "@/lib/types";
import { Button } from "@/components/Button";
import { TextArea } from "@/components/ui/TextArea";
import { StatusDot } from "@/components/ui/StatusDot";
import { IntakeExamplesPanel } from "@/components/flow/IntakeExamplesPanel";
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
    <div className="grid grid-cols-12 gap-8 lg:gap-12">
      <div className="col-span-12 flex flex-col gap-8 lg:col-span-8">
        <div>
          <h1 className="font-display text-display-lg font-semibold tracking-tight">
            Tell us what happened.
          </h1>
          <p className="mt-4 max-w-prose font-body text-lg text-text-secondary">
            Copy the denial letter, some surrounding clinical context and answer a few short questions. In
            your words and your doctor&apos;s notes, if available.
          </p>
        </div>

        <TextArea
          label="Copy the denial letter"
          name="denial_text"
          value={denial}
          onChange={(e) => {
            setDenial(e.target.value);
            setCaseId("interactive_case");
          }}
          placeholder="Dear Member, We have reviewed your request for..."
        />

        <fieldset className="flex flex-col gap-6 rounded-md border border-border-default p-6">
          <legend className="px-1 font-body text-sm font-medium text-text-primary">
            Patient and clinical details
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
          label="Important clinical context — Doctor's notes, diagnosis, treatment recommended, reason the treatment matters and should not be denied."
          name="clinical_context"
          hint="Optional."
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

      <aside className="col-span-12 lg:col-span-4 lg:sticky lg:top-28 lg:self-start">
        <IntakeExamplesPanel
          cases={cases}
          selectedCaseId={caseId === "interactive_case" ? null : caseId}
          onSelect={pickSample}
        />
      </aside>
    </div>
  );
}
