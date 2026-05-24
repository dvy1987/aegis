# Architecture — Reverse

> Companion to [PRD.md](prd/PRD.md). This document is the technical blueprint.

---

## 1. System Overview

Reverse is a single-agent system with one offline learning job, instrumented end-to-end with Arize Phoenix and using the Phoenix MCP server for runtime trace introspection.

```diagram
                  ╭───────────────────────╮
                  │   Streamlit UI        │
                  │   (Cloud Run)         │
                  ╰────────────┬──────────╯
                               │ HTTP
                  ╭────────────▼──────────╮
                  │   Reverse Agent       │
                  │   (Google ADK + Gemini 3)
                  │                       │
                  │  Tools:               │
                  │   • parse_denial_case │
                  │   • retrieve_authorities
                  │   • get_learned_playbook
                  │   • phoenix_trace_summary  ◄────╮
                  │   • draft_appeal_package │     │
                  │   • self_check_appeal │       │
                  │   • simulate_outcome  │       │ MCP
                  ╰────────┬───────┬──────╯       │
                           │       │              │
                           │       │ traces      │
                           │       ▼              │
                           │  ╭──────────────────┴──────────╮
                           │  │   Phoenix Cloud             │
                           │  │   (traces, evals,           │
                           │  │    datasets, experiments,   │
                           │  │    prompt versions)         │
                           │  ╰──────────┬──────────────────╯
                           │             │
                           │ corpus      │ traces pulled by
                           ▼             │ learning job
                  ╭────────────────────╮ │
                  │  Local Corpus +    │ │
                  │  Playbooks (git)   │ │
                  │   • authorities/   │ │
                  │   • playbooks/     │ │
                  │   • prompts/       │ │
                  ╰────────┬───────────╯ │
                           ▲             │
                           │ promoted    │
                           │ patches     │
                  ╭────────┴─────────────▼─────╮
                  │   Learning Job (learn.py)  │
                  │   (manual trigger)         │
                  │                            │
                  │   1. Pull failed traces    │
                  │   2. Cluster by slice      │
                  │   3. Propose patch         │
                  │   4. Run experiment        │
                  │   5. Surface for approval  │
                  ╰────────────────────────────╯
```

---

## 2. Components

### 2.1 Streamlit UI (Cloud Run)
- Single-page demo app
- 3 screens: **Case Workbench**, **Phoenix Insights** (links out + summary), **Pending Learning Proposals**
- No auth; demo only
- Cloud Run min-instance = 1 during demo period (avoid cold start)

### 2.2 Reverse Agent (Google ADK + Gemini 3)
- Single ADK agent
- 7 runtime tools (see §3)
- System prompt + workflow prompt versioned in `src/prompts/` and registered in Phoenix Prompts
- Instrumented with `openinference-instrumentation-google-adk`

### 2.3 Phoenix Cloud
- Project: `reverse-hackathon`
- Stores: traces, evals (LLM-as-judge), datasets (12 benchmark cases as train/holdout splits), experiments (v1 vs vN comparisons), prompts (versioned)
- Surfaced via MCP server (`@arizeai/phoenix-mcp` configured in agent runtime)

### 2.4 Local Corpus + Playbooks (git)
- `corpus/authorities/` — markdown files of public appeal-rights texts, statutory excerpts, insurer-published appeal instructions
- `playbooks/<insurer>__<denial_type>.json` — versioned per-slice tactics
- `src/prompts/` — versioned system + workflow prompts

### 2.5 Learning Job (`learn.py`)
- Standalone Python script, triggered manually during build & demo prep
- Inputs: Phoenix project name, slice filter
- Outputs: candidate patch JSON file + Phoenix experiment results
- **Human approval gate**: the UI shows pending patches; user clicks to promote

---

## 3. Agent Tools (Detailed)

### T1 — `parse_denial_case(text_or_pdf) → CaseJSON`
- LLM-call (Gemini 3) with strict JSON schema
- Output schema enforced via `response_mime_type=application/json`
- Fields: insurer, plan_type, denial_type, service_or_procedure (+ CPT if extractable), diagnosis_summary, state, cited_denial_reason, deadlines_mentioned, missing_facts[]

### T2 — `retrieve_authorities(case_json) → [Snippet]`
- BM25 or keyword retrieval over `corpus/authorities/` (no vector DB needed at this scale)
- Returns top 5 snippets with `doc_id`, `source_url`, `excerpt`

### T3 — `get_learned_playbook(insurer, denial_type) → PlaybookJSON`
- Reads `playbooks/{insurer}__{denial_type}.json` (latest promoted version)
- Returns rules array, e.g.:
  ```json
  {
    "version": "v3",
    "rules": [
      "Quote the plan's medical-necessity definition verbatim before citing general appeal rights.",
      "If denial cites 'insufficient clinical documentation', explicitly request peer-to-peer review."
    ],
    "promoted_at": "2026-05-24T14:30:00Z",
    "promoted_from_experiment": "exp_a3b9..."
  }
  ```

### T4 — `phoenix_trace_summary(filter) → Summary`
- **MCP-backed tool** — calls `@arizeai/phoenix-mcp`
- Filter example: `{insurer: "Cigna", denial_type: "medical_necessity", quality_score__lt: 3}`
- Returns:
  - Number of matching traces
  - Top 3 failure patterns (LLM-summarized from low-scoring traces)
  - Top 3 success traits (from high-scoring traces)
  - Current prompt_version + playbook_version in use

### T5 — `draft_appeal_package(case_json, authorities, playbook, trace_summary) → AppealPackage`
- LLM call with structured output
- AppealPackage schema:
  ```json
  {
    "case_summary": "...",
    "denial_grounds_interpreted": "...",
    "appeal_strategy": "...",
    "appeal_letter": "...",
    "citations_used": [{"doc_id": "...", "quoted_text": "..."}],
    "missing_evidence_checklist": ["..."],
    "risk_flags": ["..."],
    "safety_disclaimer": "Not legal or medical advice. Draft assistance only."
  }
  ```

### T6 — `self_check_appeal(appeal_package, case_json, authorities) → SelfCheck`
- LLM call that verifies:
  - Each `citations_used[*].doc_id` exists in `authorities`
  - Each `citations_used[*].quoted_text` substring-matches the doc
  - Facts in `appeal_letter` match `case_json`
  - `missing_facts` from input are reflected in `missing_evidence_checklist`
  - No statute/regulation cited that isn't in the corpus
- Returns `{passed: bool, issues: [...]}`
- Failures are surfaced as risk_flags and logged to Phoenix

### T7 — `simulate_outcome(appeal_package) → SimulatorResult` (demo only)
- Two-step (see PRD §9.3):
  1. Feature extraction (LLM judge marks 10 features Y/N)
  2. Deterministic scoring (`eval/simulator_rules.json`)
- Returns `{score, outcome, feature_flags, explanation}`

---

## 4. Data Schemas

### 4.1 CaseJSON
```json
{
  "case_id": "case_001",
  "insurer": "Cigna",
  "plan_type": "commercial",
  "denial_type": "medical_necessity",
  "service_or_procedure": {"name": "MRI lumbar spine", "cpt": "72148"},
  "diagnosis_summary": "Chronic low back pain with radiculopathy, 8+ weeks failed conservative treatment.",
  "state": "TX",
  "cited_denial_reason": "Service does not meet medical necessity criteria per InterQual.",
  "deadlines_mentioned": ["180 days from denial date"],
  "missing_facts": ["Date of denial letter not provided", "Plan summary not attached"]
}
```

### 4.2 Phoenix Trace Metadata (set on every run)
```
case_id, insurer, denial_type, plan_type, state, service_category,
prompt_version, playbook_version, dataset_split, run_mode (v1 | v3 | live)
```

### 4.3 Learning Patch (proposal JSON)
```json
{
  "proposal_id": "patch_2026-05-24_001",
  "slice": {"insurer": "Cigna", "denial_type": "medical_necessity"},
  "patch_type": "playbook",
  "diff": {
    "add_rules": ["Quote plan medical-necessity definition before general rights."],
    "remove_rules": []
  },
  "evidence_trace_ids": ["trace_abc", "trace_def"],
  "experiment_result": {
    "current_score": 0.62,
    "candidate_score": 0.79,
    "lift": 0.17,
    "safety_delta": 0.0
  },
  "status": "pending_approval"
}
```

---

## 5. The Self-Improvement Loop (Mechanically)

### 5.1 Runtime Loop (every appeal)
1. User submits case
2. `parse_denial_case` → CaseJSON
3. `retrieve_authorities` → relevant public corpus snippets
4. `get_learned_playbook(insurer, denial_type)` → current promoted playbook
5. **`phoenix_trace_summary({insurer, denial_type, quality_score__lt: 3})` → failure patterns** (this is the MCP load-bearing step)
6. `draft_appeal_package(...)` consumes ALL the above as context
7. `self_check_appeal` → pass/fail + issues
8. (Demo) `simulate_outcome` → score
9. Trace + all evals land in Phoenix

### 5.2 Batch Learning Loop (manual trigger, ~3 times during build)
1. `learn.py --slice cigna+medical_necessity`
2. Pull all traces in that slice from Phoenix
3. Identify low-scoring runs (composite < 0.55)
4. Cluster failure modes (LLM summarization over failure traces)
5. Compare failure traits vs success traits feature-by-feature
6. Propose patch (prompt fragment OR playbook OR both)
7. Run Phoenix Experiment: current vs candidate on the 6 held-out cases
8. Output proposal JSON with experiment results
9. UI shows proposal → user reviews → approves or rejects
10. On approve: bump prompt_version or playbook_version, update file, archive proposal
11. Next runtime uses the new version

### 5.3 Promotion Gates (hard rules)
A candidate is NEVER auto-promoted. Even after approval, these gates apply:
- ✅ Composite score lift ≥ +5% on held-out
- ✅ Safety score does not regress
- ✅ Hallucination rate stays 0
- ✅ User clicks approve

If any gate fails → rejected, archived with reason.

---

## 6. Phoenix Configuration

### 6.1 Phoenix Project Structure
- **Project name:** `reverse-hackathon`
- **Datasets:**
  - `benchmark_train_v1` (6 cases)
  - `benchmark_holdout_v1` (6 cases)
- **Prompts (versioned):**
  - `system_prompt` (v1 → v3)
  - `workflow_prompt` (v1 → v3)
- **Evals (one judge per metric, see PRD §9.2):**
  - `eval_grounding`
  - `eval_specificity`
  - `eval_evidence_completeness`
  - `eval_tactic_alignment`
  - `eval_safety`
- **Experiments:**
  - `exp_baseline_v1_holdout`
  - `exp_cigna_med_nec_v2`
  - `exp_cigna_med_nec_v3`
  - (one per learning iteration)

### 6.2 Phoenix MCP Server Config (in agent runtime)
```json
{
  "mcpServers": {
    "phoenix": {
      "command": "npx",
      "args": ["-y", "@arizeai/phoenix-mcp"],
      "env": {
        "PHOENIX_API_KEY": "${PHOENIX_API_KEY}",
        "PHOENIX_HOST": "https://app.phoenix.arize.com"
      }
    }
  }
}
```

The ADK agent registers the MCP server as a tool source, exposing trace-query capabilities to `phoenix_trace_summary`.

---

## 7. Repository Layout

```
elessar/
├── README.md
├── LICENSE                              # Apache 2.0
├── AGENTS.md                            # Agent guidance
├── pyproject.toml                       # Python project (uv or poetry)
├── .env.example                         # template; .env in .gitignore
│
├── docs/
│   ├── challenge.md
│   ├── ideas.md
│   ├── architecture.md                  # this file
│   ├── open-questions.md
│   ├── prd/PRD.md
│   ├── specs/                           # design specs (brainstorming output)
│   └── memory/                          # project memory for agents
│
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── agent.py                     # ADK agent definition
│   │   ├── tools/
│   │   │   ├── parse_denial_case.py
│   │   │   ├── retrieve_authorities.py
│   │   │   ├── get_learned_playbook.py
│   │   │   ├── phoenix_trace_summary.py # MCP-backed
│   │   │   ├── draft_appeal_package.py
│   │   │   ├── self_check_appeal.py
│   │   │   └── simulate_outcome.py
│   │   └── schemas.py                   # Pydantic models
│   ├── prompts/
│   │   ├── system_prompt_v1.md
│   │   ├── system_prompt_v3.md          # added on promotion
│   │   ├── workflow_prompt_v1.md
│   │   └── workflow_prompt_v3.md
│   ├── ui/
│   │   └── app.py                       # Streamlit
│   └── learning/
│       └── learn.py                     # offline job
│
├── corpus/
│   ├── authorities/                     # markdown files
│   │   ├── erisa_section_502.md
│   │   ├── aca_section_2719.md
│   │   ├── healthcare_gov_appeals.md
│   │   ├── aetna_appeal_process.md
│   │   ├── cigna_appeal_process.md
│   │   └── uhc_appeal_process.md
│   └── README.md
│
├── playbooks/
│   ├── aetna__medical_necessity.json
│   ├── aetna__prior_auth.json
│   ├── cigna__medical_necessity.json
│   ├── cigna__prior_auth.json
│   ├── uhc__medical_necessity.json
│   └── uhc__prior_auth.json
│
├── eval/
│   ├── cases/
│   │   ├── case_001.json … case_012.json
│   ├── judges/                          # Phoenix eval prompts
│   │   ├── grounding.md
│   │   ├── specificity.md
│   │   ├── evidence_completeness.md
│   │   ├── tactic_alignment.md
│   │   └── safety.md
│   ├── simulator_rules.json             # transparent rule set
│   └── dataset_card.md                  # provenance + ethics
│
├── proposals/                           # learning job outputs awaiting approval
│   └── archive/                         # accepted + rejected history
│
├── scripts/
│   ├── deploy_cloud_run.sh
│   ├── run_baseline_benchmark.py
│   └── run_full_eval.py
│
└── tests/
    ├── unit/
    └── integration/
```

---

## 8. Deployment

### 8.1 Local Dev
- `uv pip install -r requirements.txt`
- `streamlit run src/ui/app.py`
- Phoenix Cloud account + API key in `.env`

### 8.2 Cloud Run
- Container: `python:3.11-slim` + project deps
- `Procfile`-style entrypoint: `streamlit run src/ui/app.py --server.port=$PORT`
- Build & deploy via `gcloud run deploy` (script in `scripts/deploy_cloud_run.sh`)
- Min instances = 1 during demo period
- Region: `us-central1` (close to Gemini + Phoenix)

---

## 9. Security & Privacy

- No PHI ever (enforced by pre-commit scan + `eval/dataset_card.md` assertion)
- API keys in `.env` (gitignored); template in `.env.example`
- Phoenix Cloud is the only outbound data sink; verify no PHI leaks
- No user accounts; demo-only single tenant
- All disclaimers visible in UI

---

## 10. Open Architecture Decisions

Tracked in [docs/open-questions.md](open-questions.md). Highlights:
- Streamlit vs Gradio vs FastAPI+HTMX (defaulting to Streamlit)
- BM25 vs simple keyword for corpus retrieval (defaulting to BM25 via `rank_bm25`)
- ADK vs raw `google-genai` SDK (defaulting to ADK per hackathon rules)
- Phoenix Cloud vs self-hosted (defaulting to Cloud — free tier sufficient)
