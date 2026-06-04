"""Synthetic case generator for Aegis.

Canonical path: LLM Gemini producer→critic swarm (``llm_pipeline.py`` / ``llm_agents.py``),
grounded on the clinical KB and gated by the flaw-injection verifier (J6 contract).

Run: ``cd backend && uv run python -m app.case_generator.cli --help``

Deprecated (retained, not wired): ``aplus/`` deterministic templates + manual swarm.
"""

from __future__ import annotations

__version__ = "1.0.0"
