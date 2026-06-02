/** Settings for the live consumer flow (`/appeal` only). */

const DISCOVERY_KEY = "aegis_discovery_enabled";
const API_BASE_KEY = "aegis_api_base";

const DEFAULT_API = "http://localhost:8001";

export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const stored = window.localStorage.getItem(API_BASE_KEY);
    if (stored?.trim()) return stored.trim().replace(/\/$/, "");
  }
  const fromEnv = process.env.NEXT_PUBLIC_AEGIS_API?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  return DEFAULT_API;
}

export function setApiBase(url: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(API_BASE_KEY, url.trim().replace(/\/$/, ""));
}

export function getDiscoveryEnabled(): boolean {
  if (typeof window === "undefined") return true;
  const stored = window.localStorage.getItem(DISCOVERY_KEY);
  if (stored === "false") return false;
  return true;
}

export function setDiscoveryEnabled(enabled: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DISCOVERY_KEY, enabled ? "true" : "false");
}

export type BackendStatus = "unknown" | "checking" | "connected" | "offline";

export const SETTINGS_CHANGED_EVENT = "aegis-settings-changed";

export function notifySettingsChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(SETTINGS_CHANGED_EVENT));
}

export async function checkBackendHealth(apiBase: string): Promise<BackendStatus> {
  try {
    const res = await fetch(`${apiBase.replace(/\/$/, "")}/health`, {
      method: "GET",
      cache: "no-store",
    });
    if (!res.ok) return "offline";
    const data = (await res.json()) as { ok?: boolean };
    return data.ok ? "connected" : "offline";
  } catch {
    return "offline";
  }
}
