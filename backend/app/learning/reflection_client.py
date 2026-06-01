from __future__ import annotations

import os
from typing import Protocol

from app.learning.models import Component, DimensionSignal, ScoredRun

# Hard constraints injected into every reflection so safety/firewall survive optimization.
_REFLECTION_CONSTRAINTS = (
    "Keep the exact disclaimer, citation-only rule, and no-exclamation rule intact. "
    "Change at most ~200 tokens. Do NOT optimize toward the insurer APPROVE/DENY verdict; "
    "improve the QUALITY dimension named below. You may see only the documents and the "
    "laundered improvement notes — never an answer key."
)

# Named meta-prompt variants (the optimizer's OWN instruction — A/B'd in Tier 2 Task 3).
# "base" = the original critique-first instruction. "critique_plus" = a stricter framing that
# forces an explicit, named single-flaw diagnosis before a minimal edit (less diffuse, less padding).
_VARIANT_PREAMBLES = {
    "base": "",
    "critique_plus": (
        "BEFORE any edit, write a 2-sentence DIAGNOSIS naming the single most important "
        "specific flaw on the weakest dimension. THEN propose the MINIMAL edit that fixes "
        "exactly that flaw — do not exceed ~200 added tokens, add no new section unless it "
        "is the smallest change that closes the gap, and keep every safety rule intact.\n\n"
    ),
}


def build_reflection_prompt(*, component: Component, signal: DimensionSignal,
                            minibatch: list[ScoredRun], variant: str = "base") -> str:
    if variant not in _VARIANT_PREAMBLES:
        raise ValueError(f"unknown reflection meta-prompt variant: {variant!r}")
    notes = "\n".join(f"- {n}" for n in signal.notes.get(signal.weakest_dimension, []))
    current = component.text if component.kind == "prompt" else str(component.playbook)
    cases = "\n".join(
        f"- case {r.case_id}: {signal.weakest_dimension}={r.dimension_scores.get(signal.weakest_dimension, 1)}"
        for r in minibatch
    )
    return f"""You are improving one component of an appeal-drafting system.

{_VARIANT_PREAMBLES[variant]}FIRST CRITIQUE, THEN EDIT. Diagnose why the component underperforms on the weakest
quality dimension before proposing a change.

Weakest dimension to improve: {signal.weakest_dimension}
Current component ({component.kind}):
{current}

Minibatch (insurer-visible signal only):
{cases}

Laundered improvement notes for this dimension:
{notes}

Constraints: {_REFLECTION_CONSTRAINTS}

Return the full revised component text/JSON."""


class ReflectionClient(Protocol):
    name: str

    def reflect(self, *, component: Component, signal: DimensionSignal,
                minibatch: list[ScoredRun]) -> Component:
        """Return a revised component improving signal.weakest_dimension. Critique-first."""


def _tag_component(component: Component, dimension: str) -> Component:
    """Deterministic constructive edit: tag the component with the target dimension so
    downstream scoring can attribute and reward the improvement."""
    nxt = _bump_version(component.version)
    if component.kind == "playbook":
        pb = dict(component.playbook or {})
        pb["tactics"] = list(pb.get("tactics", [])) + [f"Address {dimension} explicitly."]
        pb["dimension_targets"] = sorted(set(pb.get("dimension_targets", [])) | {dimension})
        return component.model_copy(update={"version": nxt, "playbook": pb})
    text = (component.text or "") + f"\n- Strengthen dim:{dimension}."
    return component.model_copy(update={"version": nxt, "text": text})


def _bump_version(version: str) -> str:
    if version.startswith("v") and version[1:].isdigit():
        return f"v{int(version[1:]) + 1}"
    return f"{version}+1"


class StubReflectionClient:
    name = "stub_reflection"

    def reflect(self, *, component: Component, signal: DimensionSignal,
                minibatch: list[ScoredRun]) -> Component:
        return _tag_component(component, signal.weakest_dimension)


class GeminiReflectionClient:
    name = "gemini_reflection"

    def __init__(self, model: str | None = None, location: str = "global") -> None:
        self.model = model or os.environ.get("AEGIS_REFLECTION_MODEL", "gemini-3.1-pro")
        self.location = location

    def reflect(self, *, component, signal, minibatch) -> Component:
        from google import genai
        from google.genai import types
        prompt = build_reflection_prompt(component=component, signal=signal, minibatch=minibatch)
        try:
            client = genai.Client(vertexai=True, location=self.location)
            resp = client.models.generate_content(
                model=self.model, contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7))
            return _apply_text_edit(component, resp.text)
        except Exception:
            return component   # no-op edit on failure → loop simply finds no improvement


class AnthropicReflectionClient:
    name = "anthropic_reflection"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("AEGIS_ANTHROPIC_REFLECTION_MODEL", "claude-opus-4-8")

    def reflect(self, *, component, signal, minibatch) -> Component:
        import anthropic
        prompt = build_reflection_prompt(component=component, signal=signal, minibatch=minibatch)
        try:
            client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
            msg = client.messages.create(
                model=self.model, max_tokens=2000, temperature=0.7,
                messages=[{"role": "user", "content": prompt}])
            return _apply_text_edit(component, msg.content[0].text)
        except Exception:
            return component


def _apply_text_edit(component: Component, revised: str) -> Component:
    """Wrap an LLM's revised text back into a Component, bumping the version. For
    playbooks the model returns JSON; tolerate non-JSON by keeping the old playbook."""
    nxt = _bump_version(component.version)
    if component.kind == "prompt":
        return component.model_copy(update={"version": nxt, "text": revised.strip()})
    import json
    try:
        return component.model_copy(update={"version": nxt, "playbook": json.loads(revised)})
    except Exception:
        return component.model_copy(update={"version": nxt})
