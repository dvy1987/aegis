import { describe, expect, it } from "vitest";
import { backendUnreachableMessage, formatFetchError } from "@/lib/apiErrors";
import { AEGIS_V1_API_URL } from "@/lib/settings";

describe("apiErrors", () => {
  it("translates Safari Load failed", () => {
    const msg = formatFetchError(new Error("Load failed"), AEGIS_V1_API_URL, "Simulator");
    expect(msg).toContain("cannot reach the API");
    expect(msg).toContain(AEGIS_V1_API_URL);
  });

  it("passes through server errors", () => {
    expect(formatFetchError(new Error("Measured-lift simulator failed (500)"), AEGIS_V1_API_URL)).toBe(
      "Measured-lift simulator failed (500)",
    );
  });

  it("builds offline message with context", () => {
    expect(backendUnreachableMessage(AEGIS_V1_API_URL, "Measured-lift simulator")).toContain(
      "Measured-lift simulator",
    );
  });
});
