import os
import socket

# --- Startup patches (must run before any Google SDK imports) ---

_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if family == 0:
        return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)


socket.getaddrinfo = _ipv4_first_getaddrinfo

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("PHOENIX_PROJECT_NAME", "aegis-hackathon")
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
