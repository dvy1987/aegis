"""Synthetic case generator swarm for Aegis.

AlphaEval-aligned, per-stage independent-critic pipeline. Produces denial
cases for ``eval/cases/drafts/part-a/{train,test}/``.

Run with: ``uv run python -m app.case_generator.cli --help``.
"""

from __future__ import annotations

__version__ = "1.0.0"
