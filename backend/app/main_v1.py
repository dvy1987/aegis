import os

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

from app.aegis_v1.appeal_api import router as appeal_router
from app.app_utils.telemetry import setup_telemetry

os.environ.setdefault("PHOENIX_PROJECT_NAME", "default")
setup_telemetry()

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

app: FastAPI = get_fast_api_app(
    agents_dir=os.path.join(AGENT_DIR, "aegis_v1"),
    web=True,
    allow_origins=allow_origins,
    session_service_uri=None,
    otel_to_cloud=True,
)
app.title = "aegis-v1"
app.description = "Aegis V1 Agent API"

# Product appeal endpoint: runs the Student + Outcome Simulator and returns the
# drafted letter together with the insurer APPROVE/DENY verdict. The simulator is
# run by this orchestration layer, not as a Student tool (separation of powers).
app.include_router(appeal_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
