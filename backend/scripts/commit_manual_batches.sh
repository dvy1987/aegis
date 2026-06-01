#!/usr/bin/env bash
# Commit manual casegen in 20 batch commits (cases 11-210). Run from repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ "${1:-}" == "--infra-only" ]]; then
  git add \
    backend/app/case_generator/manual_assemble.py \
    backend/app/case_generator/manual_batches/ \
    backend/scripts/run_manual_case_batch.py \
    backend/scripts/validate_manual_batch.py \
    docs/plans/2026-06-01-manual-200-casegen-matrix.md
  git commit -m "$(cat <<'EOF'
Add manual case generation swarm (no Vertex Gemini).

Cursor-agent pipeline mirrors P1-P5 plus all stage and final-panel critics,
with schema validation and deterministic safety/PHI gates.
EOF
)"
  exit 0
fi

for b in $(seq 1 20); do
  start=$((11 + (b - 1) * 10))
  end=$((start + 9))
  for i in $(seq "$start" "$end"); do
    id=$(printf '%02d' "$i")
    git add eval/cases/drafts/benchmark-200/case_${id}_*.json
  done
  git commit -m "$(cat <<EOF
Add manual synthetic cases batch ${b} (${start}-${end}).

Generated via manual_producer swarm (cursor-manual-agent), schema-validated.
EOF
)" || echo "batch $b: nothing to commit?"
done
