import { describe, expect, it } from "vitest";
import { resolveInactiveStatusNarrative } from "@/components/showcase/console/statusNarrative";
import type { ShowcaseManifest } from "@/lib/types";

const manifest: ShowcaseManifest = {
  benchmark_id: "test",
  version: "1",
  quick_slice: "Cigna:medical_necessity",
  quick_train: [],
  quick_holdout: [{ case_id: "a" }] as ShowcaseManifest["quick_holdout"],
  serious_train_count: 5,
  serious_holdout: [{ case_id: "s_0" }, { case_id: "s_1" }] as ShowcaseManifest["serious_holdout"],
};

describe("resolveInactiveStatusNarrative", () => {
  it("describes the first preview beat before any run", () => {
    const narrative = resolveInactiveStatusNarrative(manifest, false);
    expect(narrative.justNow).toBeNull();
    expect(narrative.upNext).toContain("1 case");
    expect(narrative.upNext).toContain("Preview holdout");
    expect(narrative.upNext).toContain("baseline drafter agent");
  });

  it("points to production when preview already succeeded", () => {
    const narrative = resolveInactiveStatusNarrative(manifest, true);
    expect(narrative.justNow).toContain("Preview run completed");
    expect(narrative.upNext).toContain("2 cases");
  });
});
