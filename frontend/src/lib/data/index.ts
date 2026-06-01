import type { DataSource } from "./source";
import { demoSource } from "./demo";
import { liveSource } from "./live";

// Demo is the default so the app is always clickable offline. Set
// NEXT_PUBLIC_AEGIS_MODE=live (and optionally NEXT_PUBLIC_AEGIS_API) to call the backend.
export function getDataSource(): DataSource {
  return process.env.NEXT_PUBLIC_AEGIS_MODE === "live" ? liveSource : demoSource;
}
