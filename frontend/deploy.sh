#!/usr/bin/env bash
# Deploy the Heuristics frontend (Next.js) to Google Cloud Run.
#
# Two modes:
#   demo (default) — bundled fixtures, no backend, safest for the hackathon demo
#   live           — calls the v1 backend, requires AEGIS_API_URL
#
# Usage:
#   ./deploy.sh                                    # demo mode (default)
#   ./deploy.sh --mode demo                        # explicit demo mode
#   ./deploy.sh --mode live --api https://...      # live mode
#
# Overrides (env vars):
#   PROJECT_ID      GCP project id        (default: from gcloud config or .env)
#   REGION          Cloud Run region      (default: us-central1)
#   SERVICE_NAME    Cloud Run service     (default: aegis-frontend)
#   YES             skip [y/N] prompts    (default: unset)

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-aegis-frontend}"
MODE="demo"
AEGIS_API_URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --api)  AEGIS_API_URL="$2"; shift 2 ;;
    --project) PROJECT_ID="$2"; shift 2 ;;
    --region)  REGION="$2"; shift 2 ;;
    --service) SERVICE_NAME="$2"; shift 2 ;;
    --help|-h)
      sed -n '1,/^set -e/p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: no GCP project. Set PROJECT_ID env var or run 'gcloud config set project <id>'." >&2
  exit 1
fi

if [[ "${MODE}" != "demo" && "${MODE}" != "live" ]]; then
  echo "ERROR: --mode must be 'demo' or 'live' (got '${MODE}')." >&2
  exit 2
fi

if [[ "${MODE}" == "live" && -z "${AEGIS_API_URL}" ]]; then
  echo "ERROR: --mode live requires --api <backend-url>." >&2
  echo "       Deploy the v1 backend first (../backend/deploy-v1.sh), then re-run with --api <its url>." >&2
  exit 2
fi

cat <<EOF

About to deploy:
  Service     : ${SERVICE_NAME}
  Project     : ${PROJECT_ID}
  Region      : ${REGION}
  Mode        : ${MODE}$([ "${MODE}" = "live" ] && echo " (api=${AEGIS_API_URL})")
  Source dir  : $(pwd)
  Builder     : Cloud Build (no local Docker required)

This will create or update a public Cloud Run service. Logs will stream below.
EOF

if [[ -z "${YES:-}" ]]; then
  read -r -p "Proceed? [y/N] " ans
  [[ "${ans:-}" == "y" || "${ans:-}" == "Y" ]] || { echo "Cancelled."; exit 0; }
fi

BUILD_ARGS=(
  "--set-build-env-vars=NEXT_PUBLIC_AEGIS_MODE=${MODE}"
)
if [[ "${MODE}" == "live" ]]; then
  BUILD_ARGS+=("--set-build-env-vars=NEXT_PUBLIC_AEGIS_API=${AEGIS_API_URL}")
fi

gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --source . \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 1 \
  --max-instances 5 \
  --timeout 60s \
  --quiet \
  "${BUILD_ARGS[@]}"

URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')

cat <<EOF

Deployed.
  URL : ${URL}
  Mode: ${MODE}

Smoke-check it:
  curl -sS -o /dev/null -w 'HTTP %{http_code}\n' "${URL}/"
  curl -sS -o /dev/null -w 'HTTP %{http_code}\n' "${URL}/appeal"
  curl -sS -o /dev/null -w 'HTTP %{http_code}\n' "${URL}/showcase"
EOF
