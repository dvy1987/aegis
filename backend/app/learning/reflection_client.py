from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Protocol

from app.aegis_v1.geo_playbook import US_PLAYBOOK_COMPONENT_ID, bump_geo_version
from app.aegis_v1.question_agent import (
    QUESTION_AGENT_COMPONENT_ID,
    QUESTION_AGENT_PROMPT_INVARIANTS,
    ensure_question_agent_prompt_invariants,
)
from app.evals.part_a.question_judge import filter_question_agent_reflection_notes
from app.learning.models import Component, DimensionSignal, ScoredRun

logger = logging.getLogger(__name__)

PROMPT_WORD_CAP = 200
DRAFTER_COMPONENT_ID = "drafter_system_prompt"
_PROMPT_COMPONENT_IDS = frozenset({DRAFTER_COMPONENT_ID, QUESTION_AGENT_COMPONENT_ID})

# Hard constraints injected into every reflection so safety/firewall survive optimization.
_REFLECTION_CONSTRAINTS = (
    "Keep the exact disclaimer, citation-only rule, and no-exclamation rule intact. "
    "Do NOT optimize toward the insurer APPROVE/DENY verdict; improve letter quality "
    "using only laundered judge notes — never an answer key."
)

_CORPUS_REALITY = (
    "Runtime limits: the drafter and question agent see denial text, playbooks, library, "
    "and Phoenix memory only — no teacher packet, no rubric names, no hidden case flaws. "
    "The controlled corpus is thin on state law (mostly US federal rules in geo_playbook:us); "
    "internet search is cost-capped. Do not rewrite prompts to demand state-statute citations "
    "the runtime cannot reliably produce. Route federal/regulatory guidance to "
    "geo_playbook:us and insurer-specific tactics to the slice playbook."
)

_FORBIDDEN_PROMPT_PHRASES = (
    "appeal_vector_capture",
    "appeal vector capture",
    "maximize appeal vector",
    "weakest dimension",
    "weighted_quality",
    "hard_gate",
    "dim:grounding",
    "dim:appeal",
    "dim:case_specific",
    "dim:persuasive",
    "dim:question",
)

_PROMPT_MUTATION_RULES = f"""
PROMPT MUTATION RULES (hard — {DRAFTER_COMPONENT_ID} & {QUESTION_AGENT_COMPONENT_ID}):
- revised_component is the ONLY runnable system prompt the agent will load. Never put
  reflection_critique, CRITIQUE, DIAGNOSIS, or judge commentary inside it.
- revised_component MUST stay under {PROMPT_WORD_CAP} words (hard cap). Count before returning.
- Use plain, patient-facing language. FORBIDDEN inside revised_component: rubric dimension ids,
  internal eval jargon, dim: tags, or instructions copied from judge notes verbatim.
- Put insurer-specific denial tactics in the slice playbook; put US federal/legal rules in
  geo_playbook:us — not in the drafter or question-agent prompts.
"""

# Named meta-prompt variants (optimizer meta-instructions only — never copied to agents).
_VARIANT_PREAMBLES = {
    "base": "",
    "critique_plus": (
        "In reflection_critique, name the single most important specific flaw in plain "
        "language (no rubric dimension ids). Then make the smallest revised_component "
        f"that fixes it under {PROMPT_WORD_CAP} words.\n\n"
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

_JSON_OUTPUT_INSTRUCTION = """
Return JSON only (no markdown fences, no prose outside the object):
{
  "reflection_critique": "2-4 sentences for the learning log ONLY — diagnose the gap in plain language. Never copied into revised_component.",
  "revised_component": <string for prompts | JSON object for playbooks>
}
"""


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


def build_reflection_prompt(
    *,
    component: Component,
    signal: DimensionSignal,
    minibatch: list[ScoredRun],
    variant: str = "base",
) -> str:
    if variant not in _VARIANT_PREAMBLES:
        raise ValueError(f"unknown reflection meta-prompt variant: {variant!r}")
    notes = _reflection_improvement_notes(component, signal)
    current = component.text if component.kind == "prompt" else str(component.playbook)
    question_agent_rules = ""
    if component.component_id == QUESTION_AGENT_COMPONENT_ID:
        question_agent_rules = _QUESTION_AGENT_REFLECTION_RULES
    cases = "\n".join(
        f"- case {r.case_id}: score snapshot for improvement planning"
        for r in minibatch
    )
    playbook_rules = ""
    prompt_rules = ""
    if component.component_id in _PROMPT_COMPONENT_IDS:
        prompt_rules = _PROMPT_MUTATION_RULES
    if component.component_id == US_PLAYBOOK_COMPONENT_ID:
        recs = _question_judge_playbook_recs(signal, geo=True)
        rec_block = (
            "\nQuestion-agent judge recommendations for US-playbook (append-first):\n"
            + "\n".join(f"- {n}" for n in recs)
            + "\n"
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
            + "\n".join(f"- {n}" for n in recs)
            + "\n"
        ) if recs else ""
        playbook_rules = (
            "\nPLAYBOOK RULE — append-first: keep every existing tactic and "
            "required_evidence entry; ADD new entries instead of rewriting or "
            "deleting. Insurer-specific rules only — do not add US-wide geo rules here.\n"
            + rec_block
        )
    return f"""You are improving one component of an appeal-drafting system.

{_VARIANT_PREAMBLES[variant]}Diagnose why the component underperforms, then propose a minimal fix.
Put your diagnosis in reflection_critique only — never in revised_component.

Improvement focus (internal planning label — do not echo this id in revised_component):
{signal.weakest_dimension}

Current component ({component.kind}):
{current}

Minibatch (insurer-visible signal only):
{cases}

Laundered improvement notes:
{notes}
{_CORPUS_REALITY}
{playbook_rules}{question_agent_rules}{prompt_rules}
Constraints: {_REFLECTION_CONSTRAINTS}
{_JSON_OUTPUT_INSTRUCTION}"""


class ReflectionClient(Protocol):
    name: str

    def reflect(
        self,
        *,
        component: Component,
        signal: DimensionSignal,
        minibatch: list[ScoredRun],
    ) -> Component:
        """Return a revised component improving signal.weakest_dimension."""


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
    text = (component.text or "") + f"\n- Strengthen appeal quality on this case type."
    return component.model_copy(update={"version": nxt, "text": text})


def _bump_version(version: str) -> str:
    if version.startswith("v") and version[1:].isdigit():
        return f"v{int(version[1:]) + 1}"
    return f"{version}+1"


def _word_count(text: str) -> int:
    return len(text.split())


def _strip_fenced_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _strip_embedded_critique(text: str) -> str:
    """Remove critique preamble if the model disobeyed and inlined it."""
    cleaned = text.strip()
    if re.match(r"(?is)^(?:critique|diagnosis)\s*:", cleaned):
        parts = re.split(r"\n\s*#\s+", cleaned, maxsplit=1)
        if len(parts) > 1:
            cleaned = f"# {parts[1]}"
        else:
            cleaned = re.sub(r"(?is)^(?:critique|diagnosis)\s*:\s*", "", cleaned)
    return cleaned.strip()


def _contains_forbidden_jargon(text: str) -> bool:
    low = text.lower()
    return any(phrase in low for phrase in _FORBIDDEN_PROMPT_PHRASES)


def _validate_prompt_text(text: str) -> tuple[str | None, str | None]:
    if re.search(r"(?is)(?:^|\n)\s*(?:critique|diagnosis)\s*:", text):
        return None, "critique_in_prompt_body"
    cleaned = _strip_embedded_critique(text)
    if _contains_forbidden_jargon(cleaned):
        return None, "forbidden_jargon"
    if _word_count(cleaned) > PROMPT_WORD_CAP:
        return None, f"word_cap_exceeded:{_word_count(cleaned)}"
    return cleaned, None


def _parse_reflection_response(raw: str) -> tuple[str, Any]:
    """Parse reflection JSON. Falls back to legacy plain body for playbooks only."""
    text = _strip_fenced_json(raw)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return "", text
    if not isinstance(payload, dict):
        return "", text
    critique = str(payload.get("reflection_critique") or "").strip()
    body = payload.get("revised_component")
    if body is None:
        body = payload.get("revised_prompt") or payload.get("revised_text") or ""
    return critique, body


class StubReflectionClient:
    name = "stub_reflection"

    def reflect(
        self,
        *,
        component: Component,
        signal: DimensionSignal,
        minibatch: list[ScoredRun],
    ) -> Component:
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
            resp = generate_content_with_fallback(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7),
            )
            return _apply_text_edit(component, resp.text or "")
        except Exception:
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
            client = anthropic.Anthropic()
            msg = client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
            )
            return _apply_text_edit(component, msg.content[0].text)
        except Exception:
            return component


def _apply_text_edit(component: Component, revised: str) -> Component:
    """Parse reflection JSON, validate prompts, bump version. Rejects invalid prompts."""
    critique, body = _parse_reflection_response(revised)
    if critique:
        logger.info(
            "reflection_critique",
            extra={
                "component_id": component.component_id,
                "reflection_critique": critique,
            },
        )

    if component.kind == "prompt":
        nxt = _bump_version(component.version)
        text = str(body).strip()
        valid, reason = _validate_prompt_text(text)
        if valid is None:
            logger.warning(
                "reflection prompt rejected",
                extra={"component_id": component.component_id, "reason": reason},
            )
            return component
        if component.component_id == QUESTION_AGENT_COMPONENT_ID:
            valid = ensure_question_agent_prompt_invariants(valid)
            valid2, reason2 = _validate_prompt_text(valid)
            if valid2 is None:
                logger.warning(
                    "reflection prompt rejected after invariant reinjection",
                    extra={"component_id": component.component_id, "reason": reason2},
                )
                return component
            valid = valid2
        return component.model_copy(
            update={
                "version": nxt,
                "text": valid,
                "reflection_critique": critique or None,
            }
        )

    nxt = (
        bump_geo_version(component.version)
        if component.component_id == US_PLAYBOOK_COMPONENT_ID
        else _bump_version(component.version)
    )
    if isinstance(body, dict):
        parsed = body
    else:
        try:
            parsed = json.loads(str(body))
        except Exception:
            try:
                parsed = json.loads(_strip_fenced_json(revised))
            except Exception:
                logger.warning(
                    "reflection playbook JSON parse failed for component=%s",
                    component.component_id,
                )
                return component
    if not isinstance(parsed, dict):
        return component
    if component.component_id == US_PLAYBOOK_COMPONENT_ID:
        parsed["version"] = nxt
    return component.model_copy(
        update={
            "version": nxt,
            "playbook": parsed,
            "reflection_critique": critique or None,
        }
    )
