/** Plain-English fetch errors — Safari reports unreachable backends as "Load failed". */

import { AEGIS_V1_API_URL } from "@/lib/settings";

const NETWORK_ERROR_RE = /load failed|failed to fetch|networkerror|network error|fetch failed/i;

export function backendUnreachableMessage(apiBase: string, context = "Request"): string {
  return (
    `${context}: cannot reach ${apiBase}. ` +
    `Confirm the drafting service is up (${AEGIS_V1_API_URL}/health).`
  );
}

export function formatFetchError(error: unknown, apiBase: string, context = "Request"): string {
  if (error instanceof Error && NETWORK_ERROR_RE.test(error.message)) {
    return backendUnreachableMessage(apiBase, context);
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return `${context} failed.`;
}
