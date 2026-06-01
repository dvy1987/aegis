import { describe, it, expect } from "vitest";
import { CASES } from "@/lib/fixtures/cases";
import { FORBIDDEN_FIXTURE_KEYS } from "@/lib/schema";

describe("firewall: consumer fixtures carry no teacher answer key", () => {
  it("has all 10 test cases", () => {
    expect(CASES).toHaveLength(10);
    expect(new Set(CASES.map((c) => c.case_id)).size).toBe(10);
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
