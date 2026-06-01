import os

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

from app.aegis_swarm.appeal_api import router as swarm_appeal_router
from app.app_utils.telemetry import setup_telemetry

os.environ.setdefault("PHOENIX_PROJECT_NAME", "aegis-swarm")
setup_telemetry()

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

app: FastAPI = get_fast_api_app(
    agents_dir=os.path.join(AGENT_DIR, "aegis_swarm"),
    web=True,
    allow_origins=allow_origins,
    session_service_uri=None,
    otel_to_cloud=True,
)
app.title = "aegis-swarm"
app.description = "Aegis Swarm Agent API"
app.include_router(swarm_appeal_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
