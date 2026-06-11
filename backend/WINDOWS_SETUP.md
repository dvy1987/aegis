# Windows Machine Setup Guide

This guide provides the exact commands needed to get the Heuristics backend running on a Windows machine in perfect sync with your Mac environment.

## 1. Install the Core Tools

Open **PowerShell** and run the following commands to install `uv` (our Python package manager) and `Node.js` (required for `npx` and the Phoenix MCP server).

```powershell
# Install 'uv' via PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install Node.js (if you don't already have it installed)
winget install OpenJS.NodeJS
```

> **Note:** You may need to close and reopen your PowerShell window after installing these so the new commands are recognized in your path.

## 2. Set Up the Project

Once you have cloned the repository to your Windows machine, navigate into the backend folder and sync the environment. `uv` will automatically download Python 3.11 if it's missing, create the isolated `.venv`, and precisely install every package matching your Mac's `uv.lock` file.

```powershell
# Navigate to the backend directory
cd path\to\aegis\backend

# Sync dependencies and create the environment
uv sync
```

## 3. Set Up Environment Variables

You need to create your `.env` file just like on the Mac.

```powershell
# Copy the example file to create your actual .env
Copy-Item .env.example .env
```

Open the newly created `.env` file in your editor (e.g., VS Code or Notepad) and paste in your credentials:

```env
PHOENIX_API_KEY=*************** (your API key here)
# Do not set PHOENIX_PROJECT_NAME here — each backend pins its own project at startup:
#   main_v1.py → default; main_swarm.py → aegis-swarm
PHOENIX_HOST=https://app.phoenix.arize.com/s/iitk-divya
GOOGLE_CLOUD_PROJECT=gen-lang-client-0362343014
GOOGLE_CLOUD_LOCATION=global
GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

## 4. Authenticate with Google Cloud

The backend uses `google.auth.default()` to call the Gemini API through your GCP project. Being logged into `gcloud` CLI is **not enough** — Python libraries need a separate credential file called **Application Default Credentials (ADC)**.

```powershell
# Install gcloud CLI if you don't have it
# Download from: https://cloud.google.com/sdk/docs/install

# Log into gcloud CLI (if you haven't already)
gcloud auth login

# Create Application Default Credentials (this is the one Python needs)
gcloud auth application-default login
```

The second command opens a browser — sign in with your Google account, and it creates a credentials file at `%APPDATA%\gcloud\application_default_credentials.json` that Python auto-discovers.

> **Important:** `gcloud auth login` and `gcloud auth application-default login` are two different auth stores. The first lets the `gcloud` CLI work; the second lets your Python code work. You need both.

## 5. Verify the Setup

Run the test script to ensure your Windows machine can successfully talk to Arize Phoenix, then start the backend to confirm Google auth works:

```powershell
# Verify Phoenix MCP connection
uv run python test_mcp_standalone.py

# Verify backend v1 starts and Google auth works
uv run uvicorn app.main_v1:app --host 127.0.0.1 --port 8001
```

In a separate terminal, check the health endpoint:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

If you get `{"ok": true}`, your Windows machine is fully armed and ready to build!

To start both backend services and the frontend, use the dev launcher:

```powershell
.\scripts\dev.ps1
```

This starts:
- **Backend v1** on port 8001 (Phoenix project: **`default`** — pinned in `main_v1.py`)
- **Backend swarm** on port 8002 (Phoenix project: **`aegis-swarm`** — pinned in `main_swarm.py`)
- **Frontend** on port 3000
