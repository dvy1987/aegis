/** Public showcase hosts where preview/production runs must stay off (Gemini cost). */
const BLOCKED_SHOWCASE_HOSTS = new Set(["aegis-frontend-v6a3eydpoq-uc.a.run.app"]);

/** Build-time kill switch for live showcase run controls (appeal path ignores this). */
export function showcaseRunsEnabledFromBuild(): boolean {
  return process.env.NEXT_PUBLIC_AEGIS_SHOWCASE_RUNS_DISABLED !== "true";
}

/** Client-side guard for the deployed public showcase URL. */
export function showcaseRunsEnabledOnHost(): boolean {
  if (typeof window === "undefined") return true;
  if (BLOCKED_SHOWCASE_HOSTS.has(window.location.hostname)) return false;
  return showcaseRunsEnabledFromBuild();
}
