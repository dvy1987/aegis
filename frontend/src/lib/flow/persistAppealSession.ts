import type { FlowState } from "@/lib/flow/reducer";

const STORAGE_KEY = "aegis-appeal-session-v1";

export interface PersistedAppealSession {
  version: 1;
  savedAt: string;
  state: FlowState;
}

const RESUMABLE_STEPS = new Set<FlowState["step"]>(["mirror", "draft", "decide"]);

export function canPersistAppealSession(state: FlowState): boolean {
  return Boolean(state.result && state.req && RESUMABLE_STEPS.has(state.step));
}

export function saveAppealSession(state: FlowState): boolean {
  if (typeof window === "undefined" || !canPersistAppealSession(state)) return false;
  const payload: PersistedAppealSession = {
    version: 1,
    savedAt: new Date().toISOString(),
    state,
  };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    return true;
  } catch {
    return false;
  }
}

export function loadAppealSession(): PersistedAppealSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedAppealSession;
    if (parsed.version !== 1 || !parsed.state?.result || !parsed.state.req) return null;
    if (!RESUMABLE_STEPS.has(parsed.state.step)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearAppealSession(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function formatSavedAt(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}
