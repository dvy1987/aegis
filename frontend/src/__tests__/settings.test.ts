import { describe, it, expect, beforeEach } from "vitest";
import {
  getDiscoveryEnabled,
  setDiscoveryEnabled,
  setApiBase,
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

  it("persists api base", () => {
    setApiBase("http://localhost:8001");
    expect(getApiBase()).toBe("http://localhost:8001");
  });
});
