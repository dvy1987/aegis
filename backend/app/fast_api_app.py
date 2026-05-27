import os

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

from app.app_utils.telemetry import setup_telemetry

setup_telemetry()

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    allow_origins=allow_origins,
    session_service_uri=None,
    otel_to_cloud=False,
)
app.title = "aegis-backend"
app.description = "Aegis appeal-letter agent API"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
