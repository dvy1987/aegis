import { describe, expect, it } from "vitest";
import { consolidateGapItems } from "@/lib/flow/consolidateGapItems";

describe("consolidateGapItems", () => {
  it("merges formulary letter gaps into at most three bullets for case 168", () => {
    const raw = [
      "Confirm with your oncologist whether they sent the insurer a letter explaining why this treatment is needed.",
      "Ask your doctor which medication the plan considers the preferred alternative, and whether they can send a letter explaining why it is not appropriate for you.",
      "If your doctor already sent clinical records to the insurer, ask for a copy to keep with your appeal.",
      "Ask your prescriber whether they submitted a formulary-exception or supporting letter — and request a copy if they did.",
      "Gather office notes, lab results, or imaging your doctor has that show why you need this treatment now.",
    ];
    const out = consolidateGapItems(raw);
    expect(out.length).toBeLessThanOrEqual(3);
    expect(out.join(" ")).toMatch(/preferred|letter/i);
    expect(out.join(" ")).toMatch(/records|labs|imaging/i);
    expect(out.filter((line) => /letter/i.test(line)).length).toBe(1);
  });
});
