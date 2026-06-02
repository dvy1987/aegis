"""Offline Gumloop-style swarm runner.

This package mirrors the repo's `gumloop/` prompt architecture, but runs fully
offline (no external LLM calls) using deterministic critics + safe auto-fixes.

It is intended for pre-flight hygiene before running the real Gumloop flow with
a different model.
"""

