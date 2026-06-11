import os
import socket

# --- Startup patches (must run before any Google SDK imports) ---

# Force IPv4: macOS resolves Google APIs to IPv6 first, but IPv6 is
# unreachable on this machine, causing every Python HTTP call to hang
# (curl works because it falls back to IPv4 automatically).
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_first_getaddrinfo

# Fix Vertex AI location: "global" causes 155s+ latency or hangs;
# us-central1 is the regional endpoint that actually responds.
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

# Phoenix project name is pinned by the v1 backend so the host env cannot
# override it and bleed traces into another project. v1 = "default"; the
# swarm service uses its own project. See AGENTS.md (root) and ADR-006.
os.environ["PHOENIX_PROJECT_NAME"] = "default"
print(f"[main_v1] PHOENIX_PROJECT_NAME={os.environ['PHOENIX_PROJECT_NAME']}")

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

from app.aegis_v1.appeal_api import router as appeal_router
from app.aegis_v1.showcase_api import router as showcase_router
from app.app_utils.telemetry import setup_telemetry

setup_telemetry()

_dev_origins = "http://localhost:3000,http://127.0.0.1:3000"
allow_origins = [
    origin.strip()
    for origin in os.getenv("ALLOW_ORIGINS", _dev_origins).split(",")
    if origin.strip()
]

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

app: FastAPI = get_fast_api_app(
    agents_dir=os.path.join(AGENT_DIR, "aegis_v1"),
    web=True,
    allow_origins=allow_origins,
    session_service_uri=None,
    otel_to_cloud=True,
)
app.title = "aegis-v1"
app.description = "Heuristics V1 Agent API"

# Product appeal endpoint: runs the Student + Outcome Simulator and returns the
# drafted letter together with the insurer APPROVE/DENY verdict. The simulator is
# run by this orchestration layer, not as a Student tool (separation of powers).
app.include_router(appeal_router)
app.include_router(showcase_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
