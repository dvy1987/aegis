import { describe, it, expect } from "vitest";
import { demoSource } from "@/lib/data/demo";

describe("demoSource", () => {
  it("lists 3 measured-lift sample cases", async () => {
    expect(await demoSource.listCases()).toHaveLength(3);
  });
  it("drafts an appeal for a known case", async () => {
    const r = await demoSource.draftAppeal({
      denial_text: "x",
      case_id: "case_168_aetna_priorauth",
      insurer: "Aetna",
      patient_age: 53,
      patient_gender: "F",
    });
    expect(r.outcome.verdict === "APPROVE" || r.outcome.verdict === "DENY").toBe(true);
    expect(r.appeal_letter.length).toBeGreaterThan(50);
  });
  it("falls back for an unknown case id", async () => {
    const r = await demoSource.draftAppeal({
      denial_text: "x",
      case_id: "nope",
      insurer: "Aetna",
      patient_age: 30,
      patient_gender: "F",
    });
    expect(r.appeal_letter.length).toBeGreaterThan(50);
  });
  it("returns an unmeasured showcase bundle with zero lift", async () => {
    const s = await demoSource.getShowcase("case_168_aetna_priorauth");
    expect(s.measured).toBe(false);
    expect(s.lift_relative_pct).toBe(0);
  });
});
