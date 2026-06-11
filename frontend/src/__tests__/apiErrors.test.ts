import { describe, expect, it } from "vitest";
import { backendUnreachableMessage, formatFetchError } from "@/lib/apiErrors";

describe("apiErrors", () => {
  it("translates Safari Load failed into a backend hint", () => {
    const msg = formatFetchError(new Error("Load failed"), "http://localhost:8001", "Simulator");
    expect(msg).toContain("cannot reach the API");
    expect(msg).toContain("8001");
    expect(msg).toContain("uvicorn");
  });

  it("passes through server errors", () => {
    expect(formatFetchError(new Error("Measured-lift simulator failed (500)"), "http://localhost:8001")).toBe(
      "Measured-lift simulator failed (500)",
    );
  });

  it("builds offline message with context", () => {
    expect(backendUnreachableMessage("http://localhost:8001", "Measured-lift simulator")).toContain(
      "Measured-lift simulator",
    );
  });
});
