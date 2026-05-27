from fastapi.testclient import TestClient
from backend.app.fast_api_app import app

client = TestClient(app)
response = client.get("/health")
print(f"Status Code: {response.status_code}")
print(f"Response: {response.json() if response.status_code == 200 else response.text}")
