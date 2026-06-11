import { describe, it, expect, beforeEach } from "vitest";
import {
  AEGIS_V1_API_URL,
  getDiscoveryEnabled,
  setDiscoveryEnabled,
  getApiBase,
} from "@/lib/settings";

describe("settings", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults discovery on", () => {
    expect(getDiscoveryEnabled()).toBe(true);
  });

  it("persists explicit discovery off", () => {
    setDiscoveryEnabled(false);
    expect(getDiscoveryEnabled()).toBe(false);
  });

  it("always points at the fixed cloud v1 api", () => {
    expect(getApiBase()).toBe(AEGIS_V1_API_URL);
  });
});
