import { consolidateGapItems } from "@/lib/flow/consolidateGapItems";
import { formatMirrorBullets, paraphraseInterview } from "@/lib/flow/paraphraseInterview";
import type { AppealRequest, AppealResponse, MirrorBlock, QuestionInterview } from "@/lib/types";

function clip(text: string, max = 280): string {
  const t = text.replace(/\s+/g, " ").trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1).trim()}…`;
}

function paragraphs(text: string): string[] {
  return text
    .split(/\n+/)
    .map((p) => p.trim())
    .filter(Boolean);
}

function treatmentFromClinical(clinical?: string): string | null {
  if (!clinical) return null;
  const m = clinical.match(
    /prescribed\s+([^.]+?)(?:,|\.|\s+a\s+time-limited|\s+that\s+)/i,
  );
  return m?.[1]?.trim() ?? null;
}

function treatmentFromInterview(interview?: QuestionInterview | null): string | null {
  const text = interview?.qa_transcript?.map((t) => t.answer).join(" ") ?? "";
  const prescribed = text.match(/prescribed\s+([^.]+?)(?:\s+for|\s+because|\.)/i);
  if (prescribed?.[1]) return prescribed[1].trim();
  const named = text.match(
    /\b(venetoclax|obinutuzumab|rituximab|wegovy|mri|infusion|therapy|surgery|procedure)\b[^.]{0,80}/i,
  );
  return named?.[0]?.trim() ?? null;
}

function summarizeWhatDenied(
  denial: string,
  clinical?: string,
  interview?: QuestionInterview | null,
): string {
  const treatment = treatmentFromClinical(clinical) ?? treatmentFromInterview(interview);
  if (treatment) {
    return `Prior authorization or coverage for ${treatment}.`;
  }
  if (/prior authorization|prior auth/i.test(denial)) {
    return "Prior authorization for the treatment your doctor requested.";
  }
  if (/medical necessity/i.test(denial)) {
    return "Coverage for the treatment or procedure your doctor requested.";
  }
  if (/formulary|pharmacy/i.test(denial)) {
    return "Coverage for the medication your doctor prescribed.";
  }
  return "Coverage for the care named in the insurer's denial.";
}

function summarizeWhyDenied(denial: string): string {
  if (/formulary|preferred alternative|non-preferred tier|step therapy/i.test(denial)) {
    return (
      "The insurer says the drug is on a non-preferred formulary tier. " +
      "Their rules usually require trying a preferred alternative first — or getting your doctor to explain why that is not appropriate. " +
      "They say the records on file do not show that yet."
    );
  }
  if (/medical necessity|not medically necessary/i.test(denial)) {
    return (
      "The insurer says the care is not medically necessary under their criteria — " +
      "that the clinical information they reviewed does not support approval."
    );
  }
  if (/experimental|investigational/i.test(denial)) {
    return "The insurer is treating the service as experimental or investigational for your situation.";
  }
  if (/prior auth|prior authorization/i.test(denial) && /not obtained|without|expired/i.test(denial)) {
    return "The insurer says prior authorization was required and was not in place for this request.";
  }
  if (/exclusion|not covered under/i.test(denial)) {
    return "The insurer says this type of care is excluded or not covered under your plan terms.";
  }
  const hit =
    paragraphs(denial).find((p) =>
      /does not meet|must be tried|not establish|criteria|records available/i.test(p),
    ) ?? paragraphs(denial).find((p) => /denied/i.test(p));
  if (hit) {
    return clip(
      hit
        .replace(/^Dear Member,?\s*/i, "")
        .replace(/\bthe requested service\b/gi, "the treatment")
        .replace(/\bthe plan(?:'s)?\b/gi, "they")
        .replace(/\bAetna\b/gi, "They")
        .replace(/\bCigna\b/gi, "They")
        .replace(/\bUnitedHealthcare\b|\bUHC\b/gi, "They"),
      320,
    );
  }
  return "They applied their standard coverage rules and declined the request.";
}

function summarizeDeadline(denial: string): string {
  const dayMatch = denial.match(/(\d+)\s+days?/i);
  if (dayMatch && /appeal/i.test(denial)) {
    return `Your letter mentions a ${dayMatch[1]}-day appeal window — confirm the exact date in your plan materials and file before it passes.`;
  }
  if (/appeal/i.test(denial)) {
    return "The denial mentions an internal appeal — check your plan materials for the filing deadline.";
  }
  return "Check your plan materials for the appeal deadline, and file before that date.";
}

function mergeUniqueLines(...groups: string[][]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const group of groups) {
    for (const line of group) {
      const key = line.toLowerCase();
      if (!seen.has(key)) {
        seen.add(key);
        out.push(line);
      }
    }
  }
  return out;
}

/** Patient-actionable gaps — never simulator critique or scores. */
export function collectPatientGapItems(
  req: AppealRequest,
  interview?: QuestionInterview | null,
): string[] {
  const denial = req.denial_text;
  const items: string[] = [];
  const seen = new Set<string>();

  const add = (line: string) => {
    const key = line.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      items.push(line);
    }
  };

  if (interview?.patient_gap_note) {
    for (const line of interview.patient_gap_note.split("\n")) {
      const trimmed = line.replace(/^-\s*/, "").trim();
      if (trimmed && !trimmed.startsWith("We drafted")) add(trimmed);
    }
  }

  const answered = new Set(interview?.qa_transcript?.map((t) => t.question) ?? []);
  for (const q of interview?.planned_questions ?? []) {
    if (!answered.has(q)) add(`If you can answer this: ${q}`);
  }

  if (/formulary|preferred alternative|non-preferred tier|step therapy/i.test(denial)) {
    add(
      "Ask your doctor which medication the plan considers the preferred alternative, and whether they can send a letter explaining why it is not appropriate for you.",
    );
  }
  if (/prescriber|provider.*statement|formulary exception|letter explaining/i.test(denial)) {
    add(
      "Ask your prescriber whether they submitted a formulary-exception or supporting letter — and request a copy if they did.",
    );
  }
  if (/prior auth|prior authorization/i.test(denial) && /expired|not obtained|not received/i.test(denial)) {
    add("Confirm with your doctor's office whether a new prior-authorization request has been submitted.");
  }
  if (
    /records available|submitted records|documentation|do not establish|formulary|preferred alternative/i.test(
      denial,
    )
  ) {
    add(
      "Gather office notes, lab results, or imaging your doctor has that show why you need this treatment now, and copies of anything already sent to the insurer.",
    );
  }
  if (/medical necessity|not medically necessary|experimental|investigational/i.test(denial)) {
    add(
      "Ask your doctor for a short letter tying your diagnosis, symptoms, and prior treatments to why this care is medically necessary for you.",
    );
  }

  return items;
}

function formatGapNote(items: string[]): string {
  if (!items.length) {
    return (
      "If something above does not look right, note it before you file. " +
      "Your doctor's office can often supply supporting letters or records."
    );
  }
  return items.map((item) => `• ${item}`).join("\n\n");
}

export function buildAppealMirror(req: AppealRequest, response: AppealResponse): MirrorBlock {
  const interview = response.question_interview;
  const { helps, gaps: interviewGaps } = paraphraseInterview(interview);
  const gapItems = consolidateGapItems(
    mergeUniqueLines(interviewGaps, collectPatientGapItems(req, interview)),
  );

  return {
    insurer: req.insurer,
    what_was_denied: summarizeWhatDenied(req.denial_text, req.clinical_context, interview),
    why_they_said_no: summarizeWhyDenied(req.denial_text),
    deadline_note: summarizeDeadline(req.denial_text),
    what_helps_note: formatMirrorBullets(helps),
    gaps_note: formatGapNote(gapItems),
  };
}
