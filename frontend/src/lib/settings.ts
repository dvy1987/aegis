/** Live API calls (`/appeal`, showcase measured-lift simulator). */

const DISCOVERY_KEY = "aegis_discovery_enabled";

/** Fixed backend — aegis-v1-api on Cloud Run. Not configurable. */
export const AEGIS_V1_API_URL = "https://aegis-v1-api-v6a3eydpoq-uc.a.run.app";

export function getApiBase(): string {
  return AEGIS_V1_API_URL;
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

export async function checkBackendHealth(apiBase: string = AEGIS_V1_API_URL): Promise<BackendStatus> {
  try {
    const res = await fetch(`${apiBase.replace(/\/$/, "")}/health`, {
      method: "GET",
      cache: "no-store",
    });
    if (!res.ok) return "offline";
    const data = (await res.json()) as { ok?: boolean; status?: string };
    return data.ok || data.status === "ok" ? "connected" : "offline";
  } catch {
    return "offline";
  }
}
