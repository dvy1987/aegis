from __future__ import annotations

import logging
import os
from typing import Protocol

from app.aegis_v1.geo_playbook import US_PLAYBOOK_COMPONENT_ID, bump_geo_version
from app.aegis_v1.question_agent import (
    QUESTION_AGENT_COMPONENT_ID,
    QUESTION_AGENT_PROMPT_INVARIANTS,
    ensure_question_agent_prompt_invariants,
)
from app.evals.part_a.question_judge import filter_question_agent_reflection_notes
from app.learning.models import Component, DimensionSignal, ScoredRun

logger = logging.getLogger(__name__)

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


_QUESTION_AGENT_REFLECTION_RULES = (
    "\nQUESTION-AGENT INVARIANTS (non-negotiable — copy verbatim if missing):\n"
    + "\n".join(QUESTION_AGENT_PROMPT_INVARIANTS)
    + "\n"
    "- NEVER mutate the question agent to ask regulatory/policy/legal/plan-language "
    "questions of the patient. Regulatory gaps belong in playbooks/library lookups.\n"
    "- NEVER remove the 5-question cap, early-stop rule, or one-question-at-a-time rule.\n"
    "- Ignore any laundered note that suggests asking the patient regulatory facts; "
    "question-judge playbook_additions are for playbook reflection only.\n"
)


def _reflection_improvement_notes(component: Component, signal: DimensionSignal) -> str:
    if component.component_id == QUESTION_AGENT_COMPONENT_ID:
        raw = signal.notes.get("question_agent", [])
        filtered = filter_question_agent_reflection_notes(raw)
        notes_list = filtered
    else:
        notes_list = signal.notes.get(signal.weakest_dimension, [])
    return "\n".join(f"- {n}" for n in notes_list if n)


def _question_judge_playbook_recs(signal: DimensionSignal, *, geo: bool) -> list[str]:
    """Route question-judge mined facts to slice vs US-playbook reflection."""
    recs: list[str] = []
    for note in signal.notes.get("question_agent", []):
        low = note.lower()
        if not any(
            key in low
            for key in ("playbook addition", "add to playbook", "add to global playbook")
        ):
            continue
        is_global = "global playbook" in low
        if geo and is_global:
            recs.append(note)
        elif not geo and not is_global and "add to playbook:" in low:
            recs.append(note)
    return recs


def build_reflection_prompt(*, component: Component, signal: DimensionSignal,
                            minibatch: list[ScoredRun], variant: str = "base") -> str:
    if variant not in _VARIANT_PREAMBLES:
        raise ValueError(f"unknown reflection meta-prompt variant: {variant!r}")
    notes = _reflection_improvement_notes(component, signal)
    current = component.text if component.kind == "prompt" else str(component.playbook)
    question_agent_rules = ""
    if component.component_id == QUESTION_AGENT_COMPONENT_ID:
        question_agent_rules = _QUESTION_AGENT_REFLECTION_RULES
    cases = "\n".join(
        f"- case {r.case_id}: {signal.weakest_dimension}={r.dimension_scores.get(signal.weakest_dimension, 1)}"
        for r in minibatch
    )
    playbook_rules = ""
    if component.component_id == US_PLAYBOOK_COMPONENT_ID:
        recs = _question_judge_playbook_recs(signal, geo=True)
        rec_block = (
            "\nQuestion-agent judge recommendations for US-playbook (append-first):\n"
            + "\n".join(f"- {n}" for n in recs) + "\n"
        ) if recs else ""
        playbook_rules = (
            "\nUS-PLAYBOOK RULES:\n"
            "- DEFAULT: append a NEW rule with a NEW rule_id.\n"
            "- Before editing or revoking an existing rule, decide whether append "
            "would fix the gap without contradicting prior rules. Only edit/revoke "
            "when append is insufficient.\n"
            "- If you edit, set edit_justification on that rule. If you revoke, set "
            "revoke_justification and status=revoked. Never hard-delete rule ids.\n"
            "- scope is 'US federal' or a US state name. funding_scope is optional.\n"
            "- No invented statutes or case law — controlled corpus / letter facts only.\n"
            + rec_block
        )
    elif component.kind == "playbook":
        recs = _question_judge_playbook_recs(signal, geo=False)
        rec_block = (
            "\nQuestion-agent judge recommendations (append-first):\n"
            + "\n".join(f"- {n}" for n in recs) + "\n"
        ) if recs else ""
        playbook_rules = (
            "\nPLAYBOOK RULE — append-first: keep every existing tactic and "
            "required_evidence entry; ADD new entries instead of rewriting or "
            "deleting. Insurer-specific rules only — do not add US-wide geo rules here.\n"
            + rec_block
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
{playbook_rules}{question_agent_rules}
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
    if component.component_id == US_PLAYBOOK_COMPONENT_ID:
        from app.learning.mutation_geo import stub_append_geo_rule

        return stub_append_geo_rule(component, dimension)
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
        self.model = model or os.environ.get("AEGIS_REFLECTION_MODEL", "gemini-3.1-pro-preview")
        self.location = location

    def reflect(self, *, component, signal, minibatch) -> Component:
        from google import genai
        from google.genai import types

        from app.gemini_retry import generate_content_with_fallback

        prompt = build_reflection_prompt(component=component, signal=signal, minibatch=minibatch)
        try:
            client = genai.Client(vertexai=True, location=self.location)
            # Same model-availability fallback as the drafter/simulator/judge so
            # a missing preview model name doesn't silently stall learning.
            resp = generate_content_with_fallback(
                client.models.generate_content,
                model=self.model, contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7))
            return _apply_text_edit(component, resp.text)
        except Exception:
            # No-op edit on failure → the loop simply finds no improvement and
            # halts cleanly instead of crashing. Logged so a stalled run is
            # diagnosable (otherwise it looks like "no learning signal").
            logger.warning(
                "reflection failed for component=%s; returning unchanged (no improvement)",
                getattr(component, "component_id", "?"),
                exc_info=True,
            )
            return component


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
    if component.kind == "prompt":
        nxt = _bump_version(component.version)
        text = revised.strip()
        if component.component_id == QUESTION_AGENT_COMPONENT_ID:
            text = ensure_question_agent_prompt_invariants(text)
        return component.model_copy(update={"version": nxt, "text": text})
    nxt = (
        bump_geo_version(component.version)
        if component.component_id == US_PLAYBOOK_COMPONENT_ID
        else _bump_version(component.version)
    )
    import json
    try:
        parsed = json.loads(revised)
        if component.component_id == US_PLAYBOOK_COMPONENT_ID and isinstance(parsed, dict):
            parsed["version"] = nxt
        return component.model_copy(update={"version": nxt, "playbook": parsed})
    except Exception:
        return component.model_copy(update={"version": nxt})
