#!/usr/bin/env bash
# Deploy ONLY the Aegis v1 baseline backend (FastAPI + ADK) to Cloud Run.
#
# Service deployed: aegis-v1-api  (Dockerfile, main_v1:app, Phoenix project = aegis-baseline)
# Sibling NOT deployed by this script: aegis-swarm-api  (use a future deploy-swarm.sh)
#
# Per ADR-006, the backend ships as two isolated Cloud Run services backed by
# the same repo. This script handles only v1. If you also need the swarm
# service, deploy it separately when it exists.
#
# Required:
#   - GCP project with billing
#   - APIs enabled: Cloud Run, Cloud Build, Artifact Registry, Secret Manager,
#     Vertex AI (aiplatform.googleapis.com)
#   - PHOENIX_API_KEY available locally (in ../.env or as env var)
#
# Usage:
#   ./deploy-v1.sh                # deploy aegis-v1-api
#   ./deploy-v1.sh --bootstrap    # one-time setup: enable APIs + create secret
#
# Overrides (env vars):
#   PROJECT_ID         GCP project id    (default: from gcloud config or .env)
#   REGION             Cloud Run region  (default: us-central1)
#   SERVICE_NAME       Cloud Run service (default: aegis-v1-api)
#   PHOENIX_PROJECT    Phoenix project   (default: aegis-baseline)
#   PHOENIX_COLLECTOR  Phoenix collector (default: from .env)
#   PHOENIX_HOST_URL   Phoenix host      (default: from .env)
#   YES                skip [y/N] prompts (default: unset)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

BUILD_CONTEXT=""
cleanup() {
  if [[ -n "${BUILD_CONTEXT}" && -d "${BUILD_CONTEXT}" ]]; then
    rm -rf "${BUILD_CONTEXT}"
  fi
}
trap cleanup EXIT

prepare_build_context() {
  BUILD_CONTEXT="$(mktemp -d "${TMPDIR:-/tmp}/aegis-v1-build.XXXXXX")"
  rsync -a \
    --exclude ".venv" \
    --exclude ".pytest_cache" \
    --exclude ".ruff_cache" \
    --exclude "__pycache__" \
    --exclude "tests" \
    "${SCRIPT_DIR}/" "${BUILD_CONTEXT}/"

  mkdir -p "${BUILD_CONTEXT}/eval/benchmarks"
  cp -R "${REPO_ROOT}/eval/benchmarks/v1_showcase_100" "${BUILD_CONTEXT}/eval/benchmarks/"
  cp -R "${REPO_ROOT}/eval/cases" "${BUILD_CONTEXT}/eval/"
  cp -R "${REPO_ROOT}/eval/judges" "${BUILD_CONTEXT}/eval/"
  if [[ -f "${REPO_ROOT}/eval/denial_patterns.json" ]]; then
    cp "${REPO_ROOT}/eval/denial_patterns.json" "${BUILD_CONTEXT}/eval/"
  fi
  cp -R "${REPO_ROOT}/playbooks" "${BUILD_CONTEXT}/playbooks"
}

PROJECT_ID="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-aegis-v1-api}"
PHOENIX_PROJECT="${PHOENIX_PROJECT:-default}"
PHOENIX_COLLECTOR="${PHOENIX_COLLECTOR:-${PHOENIX_COLLECTOR_ENDPOINT:-}}"
PHOENIX_HOST_URL="${PHOENIX_HOST_URL:-${PHOENIX_HOST:-}}"
SECRET_NAME="${SECRET_NAME:-phoenix-api-key}"
BOOTSTRAP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bootstrap) BOOTSTRAP=1; shift ;;
    --project) PROJECT_ID="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --service) SERVICE_NAME="$2"; shift 2 ;;
    --phoenix-project) PHOENIX_PROJECT="$2"; shift 2 ;;
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

if [[ -z "${PHOENIX_COLLECTOR}" ]]; then
  echo "ERROR: PHOENIX_COLLECTOR_ENDPOINT not set (checked env + ../.env)." >&2
  exit 1
fi

bootstrap() {
  echo
  echo "Bootstrap — one-time setup for project ${PROJECT_ID}"
  echo "  - enable required APIs"
  echo "  - create Secret Manager secret '${SECRET_NAME}' from PHOENIX_API_KEY"
  echo "  - grant Cloud Run runtime SA access to read that secret + call Vertex AI"
  echo
  if [[ -z "${YES:-}" ]]; then
    read -r -p "Proceed? [y/N] " ans
    [[ "${ans:-}" == "y" || "${ans:-}" == "Y" ]] || { echo "Cancelled."; exit 0; }
  fi

  echo "Enabling APIs..."
  gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    aiplatform.googleapis.com \
    --project "${PROJECT_ID}"

  if [[ -z "${PHOENIX_API_KEY:-}" ]]; then
    echo "ERROR: PHOENIX_API_KEY not in environment. Source ../.env or export it before --bootstrap." >&2
    exit 1
  fi

  if gcloud secrets describe "${SECRET_NAME}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Secret '${SECRET_NAME}' already exists — adding a new version."
    printf '%s' "${PHOENIX_API_KEY}" | gcloud secrets versions add "${SECRET_NAME}" \
      --project "${PROJECT_ID}" --data-file=-
  else
    echo "Creating secret '${SECRET_NAME}'..."
    printf '%s' "${PHOENIX_API_KEY}" | gcloud secrets create "${SECRET_NAME}" \
      --project "${PROJECT_ID}" --replication-policy=automatic --data-file=-
  fi

  PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')
  RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
  echo "Granting roles to ${RUN_SA}..."
  gcloud secrets add-iam-policy-binding "${SECRET_NAME}" \
    --project "${PROJECT_ID}" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/aiplatform.user" \
    --condition=None >/dev/null

  echo "Bootstrap complete."
  echo
}

if [[ "${BOOTSTRAP}" == "1" ]]; then
  bootstrap
fi

cat <<EOF

About to deploy:
  Service           : ${SERVICE_NAME}
  Project           : ${PROJECT_ID}
  Region            : ${REGION}
  Phoenix project   : ${PHOENIX_PROJECT}
  Phoenix collector : ${PHOENIX_COLLECTOR}
  Source dir        : ${SCRIPT_DIR}
  Builder           : Cloud Build (no local Docker required)
  Secret            : ${SECRET_NAME}  (mounted as PHOENIX_API_KEY)

This will create or update a public Cloud Run service. Logs will stream below.
EOF

if [[ -z "${YES:-}" ]]; then
  read -r -p "Proceed? [y/N] " ans
  [[ "${ans:-}" == "y" || "${ans:-}" == "Y" ]] || { echo "Cancelled."; exit 0; }
fi

ENV_VARS=(
  "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
  "GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION:-global}"
  "GOOGLE_GENAI_USE_VERTEXAI=TRUE"
  "AEGIS_DRAFTER_MODEL=${AEGIS_DRAFTER_MODEL:-gemini-3.1-pro-preview}"
  "AEGIS_SIMULATOR_MODEL=${AEGIS_SIMULATOR_MODEL:-gemini-3.1-pro-preview}"
  "AEGIS_JUDGE_MODEL=${AEGIS_JUDGE_MODEL:-gemini-3.1-pro-preview}"
  "AEGIS_REFLECTION_MODEL=${AEGIS_REFLECTION_MODEL:-gemini-3.1-pro-preview}"
  "AEGIS_GEMINI_MIN_INTERVAL_SECONDS=${AEGIS_GEMINI_MIN_INTERVAL_SECONDS:-2}"
  "AEGIS_GEMINI_MAX_RETRIES=${AEGIS_GEMINI_MAX_RETRIES:-4}"
  "AEGIS_GEMINI_BACKOFF_BASE_SECONDS=${AEGIS_GEMINI_BACKOFF_BASE_SECONDS:-5}"
  "AEGIS_GEMINI_BACKOFF_MAX_SECONDS=${AEGIS_GEMINI_BACKOFF_MAX_SECONDS:-60}"
  "AEGIS_GEMINI_BACKOFF_JITTER_SECONDS=${AEGIS_GEMINI_BACKOFF_JITTER_SECONDS:-0.5}"
  "PHOENIX_PROJECT_NAME=${PHOENIX_PROJECT}"
  "PHOENIX_COLLECTOR_ENDPOINT=${PHOENIX_COLLECTOR}"
  "AEGIS_BACKEND_ROOT=/code"
  "AEGIS_REPO_ROOT=/code"
  "VERTEX_SEARCH_PROJECT=${VERTEX_SEARCH_PROJECT:-${PROJECT_ID}}"
  "VERTEX_SEARCH_LOCATION=${VERTEX_SEARCH_LOCATION:-global}"
  "VERTEX_SEARCH_DATA_STORE_ID=${VERTEX_SEARCH_DATA_STORE_ID:-}"
  "VERTEX_SEARCH_SERVING_CONFIG=${VERTEX_SEARCH_SERVING_CONFIG:-default_config}"
  "AEGIS_LIBRARY_BUCKET=${AEGIS_LIBRARY_BUCKET:-}"
  "ALLOW_ORIGINS=${ALLOW_ORIGINS:-*}"
)
if [[ -n "${PHOENIX_HOST_URL}" ]]; then
  ENV_VARS+=("PHOENIX_HOST=${PHOENIX_HOST_URL}")
fi

# Join with comma for --set-env-vars.
ENV_VARS_JOINED=$(IFS=,; echo "${ENV_VARS[*]}")

if [[ ! -f "${SCRIPT_DIR}/uv.lock" ]]; then
  echo "Generating uv.lock..."
  (cd "${SCRIPT_DIR}" && uv lock)
fi

prepare_build_context

gcloud run deploy "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --source "${BUILD_CONTEXT}" \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 2 \
  --memory 1Gi \
  --min-instances 1 \
  --max-instances 1 \
  --timeout 300s \
  --concurrency 1 \
  --no-cpu-throttling \
  --set-env-vars "${ENV_VARS_JOINED}" \
  --update-secrets "PHOENIX_API_KEY=${SECRET_NAME}:latest" \
  --quiet

URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')

cat <<EOF

Deployed.
  URL : ${URL}

Smoke-check it:
  curl -sS "${URL}/health"
  # expect: {"ok":true}

To point the frontend at THIS v1 backend, redeploy the frontend in live mode:
  cd ../frontend && ./deploy.sh --mode live --api "${URL}"

Note: the swarm backend is a separate Cloud Run service (not deployed here).
EOF
