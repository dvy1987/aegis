"""ADK Gemini model wired for Vertex AI (ADC), not the Gemini API key path.

Google ADK 2.x defaults to the Gemini API unless the model name starts with
``projects/``. Aegis runs on Vertex in dev and Cloud Run, so agents must use
this subclass.
"""

from __future__ import annotations

import os
from functools import cached_property

from google.adk.models import Gemini
from google.genai import Client


class VertexGemini(Gemini):
    """Gemini via Vertex AI using Application Default Credentials."""

    @cached_property
    def api_client(self) -> Client:
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        return Client(vertexai=True, location=location)
