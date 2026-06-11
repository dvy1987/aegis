/** Plain-English fetch errors — Safari reports unreachable backends as "Load failed". */

const NETWORK_ERROR_RE = /load failed|failed to fetch|networkerror|network error|fetch failed/i;

export const BACKEND_START_HINT =
  "cd backend && uv run uvicorn app.main_v1:app --host 0.0.0.0 --port 8001";

export function backendUnreachableMessage(apiBase: string, context = "Request"): string {
  return (
    `${context}: cannot reach the API at ${apiBase}. ` +
    `Confirm the backend is running (${BACKEND_START_HINT}) and the URL in Settings matches.`
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
