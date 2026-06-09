import type { ReactNode } from "react";

/**
 * Global Rive kill-switch. The non-Rive fallbacks ARE the product; Rive is a
 * later, optional drop-in (see build plan Phase 12). Keep this `false` until a
 * `.riv` asset is actually wired and verified to load.
 */
export const SHOWCASE_RIVE_ENABLED = false as const;

/**
 * Boundary that renders the cinematic `fallback` unless Rive is both globally
 * enabled AND an actual `rive` node is supplied. Rive never becomes a hard
 * dependency or a failure path — if it isn't there, the fallback shows.
 */
export function RiveOrFallback({
  rive,
  fallback,
  enabled = SHOWCASE_RIVE_ENABLED,
}: {
  rive?: ReactNode;
  fallback: ReactNode;
  enabled?: boolean;
}) {
  if (enabled && rive) return <>{rive}</>;
  return <>{fallback}</>;
}
