**ADR-006: Multi-Service Backend Topology and GCP Generation Job**
**Date:** 2026-05-28 | **Status:** Accepted

**Context:**
For the final 3-minute hackathon demo, we need to clearly show the contrast between the failing single-agent (Aegis v1) and the successful self-improving swarm (Part B). Additionally, the offline case generation pipeline currently requires raw API keys for Claude and Gemini, creating a security and configuration hurdle.

**Decision:**
1. **Generator on GCP (ADC):** We will run the case generation pipeline either from Google Cloud Shell or as a headless Cloud Run Job. This leverages Application Default Credentials (ADC), bypassing the need for raw API keys for both Vertex Gemini and Vertex Claude.
2. **Logical Backend Split:** We will keep a single Python backend repository but launch it as two isolated logical services (OS processes):
   - **Aegis v1 API:** Runs on Port 8001, uses `PHOENIX_PROJECT_NAME=default` (pinned in `main_v1.py`).
   - **Aegis Swarm API:** Runs on Port 8002, uses `PHOENIX_PROJECT_NAME=aegis-hackathon` (pinned in `main_swarm.py` / `Dockerfile.swarm`).

   > **Amendment (2026-06-07):** Original ADR named Phoenix projects `aegis-baseline` and `aegis-swarm`. PM confirmed deployed names are **`default`** (v1) and **`aegis-hackathon`** (swarm). There is no Phoenix project called `aegis-swarm`. See [decision-log.md §2026-06-07 Phoenix project split](../memory/decision-log.md).

**Alternatives Considered:**
- **Single Process with Dynamic Tracing:** Attempt to run both v1 and swarm in the same FastAPI app and dynamically set the Phoenix project name per request. *Rejected:* OpenTelemetry initializes global tracers at process startup. Hacking it to swap projects per-request is brittle, violates the framework's design, and risks trace leakage.
- **Physical Repository Split (`backend_v1/`, `backend_swarm/`):** Duplicate the backend scaffolding. *Rejected:* Causes massive duplication of `pyproject.toml`, Dockerfiles, linting configurations, and shared utility code. Violates DRY for a small 20-day project.
- **Generator as a Persistent Service:** Deploy the generator as a continuous Cloud Run service. *Rejected:* The generator is a batch process. Paying for an idle persistent HTTP service for a run-once batch job is wasteful.

**Consequences:**
- ✓ Complete isolation of Phoenix traces into `default` (v1) and `aegis-hackathon` (swarm) — perfect for the demo arc.
- ✓ No raw API keys needed for Claude or Gemini; full reliance on enterprise-grade GCP ADC.
- ✓ Shared Python utilities and lock files, reducing maintenance overhead.
- Tradeoff: The `scripts/dev.sh` launcher becomes slightly more complex, managing 3 processes (Next.js, API v1, API Swarm) instead of 2.
- Tradeoff: Deployment will require setting up 3 Cloud Run services instead of 2.
