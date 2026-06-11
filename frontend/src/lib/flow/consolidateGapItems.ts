/** Collapse overlapping patient-gap bullets into a short, non-repetitive list. */

type GapTheme =
  | "doctor_letter"
  | "preferred_alt"
  | "clinical_records"
  | "prior_auth"
  | "med_necessity"
  | "other";

const THEME_ORDER: GapTheme[] = [
  "doctor_letter",
  "preferred_alt",
  "clinical_records",
  "prior_auth",
  "med_necessity",
  "other",
];

const CANONICAL: Record<Exclude<GapTheme, "other">, string> = {
  doctor_letter:
    "Ask your doctor whether they sent the insurer a letter explaining why this treatment is needed — and request a copy if they did.",
  preferred_alt:
    "Ask which medication the plan treats as the preferred alternative, and why it may not be appropriate for you.",
  clinical_records:
    "Gather office notes, lab results, or imaging that support why you need this care now, plus copies of anything already sent to the insurer.",
  prior_auth:
    "Confirm with your doctor's office whether a new prior-authorization request has been submitted.",
  med_necessity:
    "Ask your doctor for a short letter tying your diagnosis, symptoms, and prior treatments to why this care is medically necessary for you.",
};

function themeOf(line: string): GapTheme {
  const l = line.toLowerCase();
  if (
    /letter|formulary exception|prescriber|oncologist.*sent|supporting letter|explaining why this treatment|explaining why it is not appropriate/.test(
      l,
    )
  ) {
    return "doctor_letter";
  }
  if (/preferred alternative|which medication the plan|step therapy|non-preferred/.test(l)) {
    return "preferred_alt";
  }
  if (/records|labs|imaging|office notes|documentation|clinical records/.test(l)) {
    return "clinical_records";
  }
  if (/prior auth|prior authorization|prior-authorization/.test(l)) {
    return "prior_auth";
  }
  if (/medically necessary|medical necessity|experimental|investigational/.test(l)) {
    return "med_necessity";
  }
  return "other";
}

function mergedFormularyGap(themes: Set<GapTheme>): string | null {
  if (!themes.has("doctor_letter") && !themes.has("preferred_alt")) return null;
  return (
    "Ask your doctor which medication the plan prefers, why it may not be right for you, " +
    "and whether they already sent the insurer a supporting or formulary-exception letter (request a copy if they did)."
  );
}

export function consolidateGapItems(items: string[]): string[] {
  if (!items.length) return [];

  const themes = new Set(items.map(themeOf));
  const others = items.filter((line) => themeOf(line) === "other");
  const out: string[] = [];

  const formularyMerge = mergedFormularyGap(themes);
  if (formularyMerge) {
    out.push(formularyMerge);
    themes.delete("doctor_letter");
    themes.delete("preferred_alt");
  }

  for (const theme of THEME_ORDER) {
    if (theme === "other") continue;
    if (themes.has(theme)) out.push(CANONICAL[theme]);
  }

  for (const line of others) {
    if (!out.some((existing) => existing.toLowerCase() === line.toLowerCase())) {
      out.push(line);
    }
  }

  return out.slice(0, 4);
}
