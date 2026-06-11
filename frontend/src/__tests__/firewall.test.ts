import { describe, it, expect } from "vitest";
import { CASES } from "@/lib/fixtures/cases";
import { parseAppealFixture, FORBIDDEN_FIXTURE_KEYS } from "@/lib/schema";

describe("firewall: consumer fixtures carry no teacher answer key", () => {
  it("has all 3 measured-lift sample cases", () => {
    expect(CASES).toHaveLength(3);
    expect(new Set(CASES.map((c) => c.case_id)).size).toBe(3);
  });
  it("contains no forbidden answer-key keys anywhere", () => {
    const blob = JSON.stringify(CASES);
    for (const k of FORBIDDEN_FIXTURE_KEYS) expect(blob).not.toContain(k);
  });
  it("every case has the student-visible fields", () => {
    for (const c of CASES) {
      expect(c.denial_letter_text.length).toBeGreaterThan(20);
      expect(c.insurer).toBeTruthy();
      expect(c.headline).toBeTruthy();
    }
  });
});

/** Demo `/appeal` fixtures only — measured-lift showcase cases draft live via the backend. */
const DEMO_APPEAL_FIXTURE_IDS = ["case_12_aetna_priorauth"] as const;

describe("appeal fixtures", () => {
  it("valid demo fixtures without answer key", async () => {
    for (const caseId of DEMO_APPEAL_FIXTURE_IDS) {
      const mod = await import(`@/lib/fixtures/appeals/${caseId}.json`);
      const fix = parseAppealFixture(mod.default);
      expect(fix.trace_metadata.case_id).toBe(caseId);
      const blob = JSON.stringify(mod.default);
      for (const k of FORBIDDEN_FIXTURE_KEYS) expect(blob).not.toContain(k);
    }
  });
  it("measured-lift showcase cases do not ship static appeal stubs", () => {
    expect(DEMO_APPEAL_FIXTURE_IDS).not.toContain(CASES[0].case_id);
  });
});
