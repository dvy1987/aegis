import { describe, it, expect } from "vitest";
import { demoSource } from "@/lib/data/demo";

describe("demoSource", () => {
  it("lists 10 cases", async () => {
    expect(await demoSource.listCases()).toHaveLength(10);
  });
  it("drafts an appeal for a known case", async () => {
    const r = await demoSource.draftAppeal({
      denial_text: "x",
      clinical_context: "",
      case_id: "test_case_03_cigna_mednec",
    });
    expect(r.outcome.verdict === "APPROVE" || r.outcome.verdict === "DENY").toBe(true);
    expect(r.appeal_letter.length).toBeGreaterThan(50);
  });
  it("falls back for an unknown case id", async () => {
    const r = await demoSource.draftAppeal({
      denial_text: "x",
      clinical_context: "",
      case_id: "nope",
    });
    expect(r.appeal_letter.length).toBeGreaterThan(50);
  });
  it("returns a showcase bundle", async () => {
    const s = await demoSource.getShowcase("test_case_03_cigna_mednec");
    expect(s.lift_relative_pct).toBeGreaterThan(0);
  });
});
