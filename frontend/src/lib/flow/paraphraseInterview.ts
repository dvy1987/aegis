import type { QuestionInterview } from "@/lib/types";

function stripUncertaintyLead(answer: string): { tentative: boolean; body: string } {
  const raw = answer.trim();
  const tentative = /^(i'?m not sure|i don'?t know|not sure|unsure)\b/i.test(raw);
  const body = raw
    .replace(/^(i'?m not sure[,.]?\s*|i don'?t know[,.]?\s*|not sure[,.]?\s*|unsure[,.]?\s*)/i, "")
    .trim();
  return { tentative, body };
}

function hasSubstance(text: string): boolean {
  return text.split(/\s+/).filter((w) => w.length > 2).length >= 4;
}

function mentionsSubmission(answer: string): boolean {
  if (
    /don'?t know if .*(sent|submitted)|not sure if .*(sent|submitted)|whether .*(sent|submitted)/i.test(
      answer,
    )
  ) {
    return false;
  }
  return /\b(sent|submitted|provided|faxed|uploaded)\b/i.test(answer);
}

function paraphraseSymptoms(body: string): string {
  const lower = body.toLowerCase();
  const parts: string[] = [];
  if (/tired|fatigue|worn out|exhausted|run-down|drained/i.test(lower)) parts.push("ongoing fatigue");
  if (/lymph node|lumps? in (?:my )?(?:neck|arms)/i.test(lower)) parts.push("swollen lymph nodes");
  if (/night sweat/i.test(lower)) parts.push("night sweats");
  if (/work|daily life|everyday|stairs|errands/i.test(lower)) {
    parts.push("difficulty keeping up with work and daily life");
  }
  if (parts.length) return `You described ${parts.join(", ")}.`;
  return `You described symptoms that are affecting your day-to-day life.`;
}

function paraphraseTreatmentHistory(body: string): string | null {
  const lower = body.toLowerCase();
  if (/first time|first treatment|my first treatment|haven'?t been treated|not tried|no other (?:med|treatment)/i.test(lower)) {
    return "This would be your first treatment for this condition — you have not tried other medications for it yet.";
  }
  if (/tried .+ (?:didn'?t|failed|not work|ineffective)/i.test(lower)) {
    return "You have tried other treatments before, and they did not work well enough for you.";
  }
  if (hasSubstance(body)) {
    return "You shared relevant background on prior treatments for this condition.";
  }
  return null;
}

function paraphraseTurn(question: string, answer: string): { helps: string[]; gaps: string[] } {
  const helps: string[] = [];
  const gaps: string[] = [];
  const { tentative, body } = stripUncertaintyLead(answer);
  const q = question.toLowerCase();

  if (/oncologist|letter|statement|prescriber|doctor submit/i.test(q)) {
    const submitted = mentionsSubmission(answer);
    const onlyUncertain =
      (tentative && !submitted) || (/don'?t know|not sure|unsure/i.test(answer) && !submitted);
    if (onlyUncertain) {
      gaps.push(
        "Confirm with your oncologist whether they sent the insurer a letter explaining why this treatment is needed.",
      );
    } else if (submitted) {
      helps.push("Your doctor's office may have already sent supporting information to the insurer.");
    } else if (hasSubstance(body)) {
      helps.push("Your oncologist is supporting this specific treatment for your condition.");
    }
    return { helps, gaps };
  }

  if (/tried any other|other medications|first time|prior treatment|medications for|starting treatment/i.test(q)) {
    const line = paraphraseTreatmentHistory(body || answer);
    if (line) helps.push(line);
    if (/symptoms|blood counts|need to begin|start (?:me |now|treatment)/i.test(body || answer)) {
      helps.push("Your doctor wants to start treatment now because of how your symptoms and test results are affecting you.");
    }
    if (!line && tentative && !hasSubstance(body)) {
      gaps.push("Clarify whether you have tried other treatments for this condition before.");
    }
    return { helps, gaps };
  }

  if (/symptom|daily life|experiencing|affecting/i.test(q)) {
    if (hasSubstance(body)) helps.push(paraphraseSymptoms(body));
    else if (tentative) {
      gaps.push("Describe how your symptoms affect daily life — that context can strengthen the appeal.");
    }
    return { helps, gaps };
  }

  if (hasSubstance(body)) {
    helps.push("You shared details that help explain your situation.");
  } else if (tentative) {
    gaps.push("One answer was uncertain — gathering that detail could strengthen the appeal.");
  }
  return { helps, gaps };
}

export function paraphraseInterview(interview?: QuestionInterview | null): {
  helps: string[];
  gaps: string[];
} {
  const helps: string[] = [];
  const gaps: string[] = [];
  const seen = new Set<string>();

  const add = (list: string[], line: string) => {
    const key = line.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      list.push(line);
    }
  };

  for (const turn of interview?.qa_transcript ?? []) {
    const answer = turn.answer.trim();
    if (!answer) continue;
    const { helps: h, gaps: g } = paraphraseTurn(turn.question, answer);
    for (const line of h) add(helps, line);
    for (const line of g) add(gaps, line);
  }

  return { helps, gaps };
}

export function formatMirrorBullets(items: string[]): string {
  if (!items.length) return "";
  return items.map((item) => `• ${item}`).join("\n\n");
}
