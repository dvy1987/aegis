import { describe, expect, it } from "vitest";
import {
  cohortMatchesCanonical,
  isLegacyShowcaseManifest,
  SHOWCASE_COHORT,
} from "@/lib/showcase/manifest";
import type { ShowcaseManifest } from "@/lib/types";

function manifest(partial: Partial<ShowcaseManifest>): ShowcaseManifest {
  return {
    benchmark_id: "v1_showcase_100",
    version: "1",
    quick_slice: "Cigna:medical_necessity",
    quick_train: [],
    quick_holdout: [],
    serious_train_count: SHOWCASE_COHORT.seriousTrain,
    serious_holdout: [],
    ...partial,
  };
}

describe("showcase manifest helpers", () => {
  it("detects legacy draft-era API payloads", () => {
    const legacy = manifest({
      quick_train: Array.from({ length: 8 }, (_, i) => ({
        case_id: `case_0${i + 1}_cigna_mednec`,
        insurer: "Cigna",
        denial_type: "medical_necessity",
        headline: "h",
        denial_letter_text: "d",
        patient_age: 40,
        patient_gender: "F",
      })),
      serious_train_count: 80,
    });
    expect(isLegacyShowcaseManifest(legacy)).toBe(true);
    expect(cohortMatchesCanonical(legacy)).toBe(false);
  });

  it("accepts canonical 3/1 + 5/2 cohort", () => {
    const current = manifest({
      quick_train: Array.from({ length: 3 }, (_, i) => ({
        case_id: `case_${101 + i}_cigna_mednec`,
        insurer: "Cigna",
        denial_type: "medical_necessity",
        headline: "h",
        denial_letter_text: "d",
        patient_age: 40,
        patient_gender: "F",
      })),
      quick_holdout: [
        {
          case_id: "case_126_cigna_mednec",
          insurer: "Cigna",
          denial_type: "medical_necessity",
          headline: "h",
          denial_letter_text: "d",
          patient_age: 40,
          patient_gender: "F",
        },
      ],
      serious_holdout: [
        {
          case_id: "case_109_aetna_mednec",
          insurer: "Aetna",
          denial_type: "medical_necessity",
          headline: "h",
          denial_letter_text: "d",
          patient_age: 40,
          patient_gender: "F",
        },
        {
          case_id: "case_106_uhc_priorauth",
          insurer: "UHC",
          denial_type: "prior_authorization",
          headline: "h",
          denial_letter_text: "d",
          patient_age: 40,
          patient_gender: "F",
        },
      ],
    });
    expect(isLegacyShowcaseManifest(current)).toBe(false);
    expect(cohortMatchesCanonical(current)).toBe(true);
  });
});
