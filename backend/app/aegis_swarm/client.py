"""Injectable LLM seam for the swarm's reasoning agents.

Mirrors Part A's ``drafter_client`` / ``simulator_client`` dependency-injection
pattern: a ``SwarmAgentClient`` Protocol with one method per reasoning role, a
``StubSwarmClient`` (deterministic, offline, used by every unit test and the
walking-skeleton dry-run), and a ``GeminiSwarmClient`` (Vertex/Gemini, live).

The pipeline (``swarm_pipeline.py``) owns all *deterministic* glue - retrieval,
guardrails, self-check, AppealPackage assembly - and calls the client only for
the parts that must reason. Each client method loads its prompt from the
registry (``prompts/registry.py``) so the active prompt version is the
credit-assignment unit the Learning Coordinator evolves.

Live generation is exercised in a GCP session (Phase 4); ``GeminiSwarmClient``
is unit-tested offline only for construction/config, exactly like Part A's
``GeminiDrafterClient`` / ``GeminiSimulatorClient``.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol, runtime_checkable

from app.aegis_swarm.corpus_store import CorpusHit
from app.aegis_swarm.schemas import (
    AdversarialCritique,
    AppealStrategy,
    BriefCitation,
    CritiqueFinding,
    InsurerBrief,
    LetterOutlineItem,
    ResearchBrief,
    ResearchFinding,
    ResearcherName,
    ResearchDepth,
    RoutingManifest,
    StrategyAngle,
)
from app.aegis_swarm.tools import (
    RESEARCHER_DOMAIN,
    build_routing,
    complexity_to_depth,
    estimate_complexity,
)

_LOG = logging.getLogger(__name__)

# Map Part A's normalized denial_type -> the swarm's denial-type vocabulary.
_DENIAL_TYPE_MAP: dict[str, str] = {
    "medical_necessity": "medical_necessity",
    "prior_authorization": "prior_auth_missing",
    "coverage_exclusion": "coverage_exclusion",
    "out_of_scope": "medical_necessity",
    "unknown": "medical_necessity",
}

_DISCLAIMER = "This letter is a draft for review — not legal or medical advice."


@runtime_checkable
class SwarmAgentClient(Protocol):
    name: str

    def triage(self, parsed_case: dict[str, Any]) -> RoutingManifest:
        """Classify denial type + complexity and pick researchers to invoke."""

    def research(
        self,
        agent: ResearcherName,
        parsed_case: dict[str, Any],
        depth: ResearchDepth,
        hits: list[CorpusHit],
        phoenix_summary: dict[str, Any] | None = None,
    ) -> ResearchBrief:
        """Turn corpus hits (already retrieved by the pipeline) into a brief.
        Returns ``InsurerBrief`` for the insurer_intelligence agent."""

    def strategize(
        self,
        parsed_case: dict[str, Any],
        briefs: list[ResearchBrief],
        manifest: RoutingManifest,
        playbook: dict[str, Any],
    ) -> AppealStrategy:
        """Synthesize the researcher briefs into an appeal strategy."""

    def draft(
        self,
        parsed_case: dict[str, Any],
        strategy: AppealStrategy,
        citations: list[CorpusHit],
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
        critique: AdversarialCritique | None = None,
    ) -> str:
        """Write the appeal-letter PROSE (no schema wrapping). The pipeline
        applies guardrails + assembles the AppealDraft, mirroring Part A."""

    def critique(
        self,
        parsed_case: dict[str, Any],
        strategy: AppealStrategy,
        letter: str,
        iteration: int = 1,
    ) -> AdversarialCritique:
        """Adversarially review the letter as a hostile insurer reviewer."""


# --- Stub (deterministic, offline) ------------------------------------------


def _brief_domain(agent: ResearcherName):
    return RESEARCHER_DOMAIN.get(agent, "legal")


# Per-researcher risk flag when retrieval comes back empty. Each domain reports
# its own "nothing found" signal (the Strategist + credit-assignment read these),
# mirroring the per-agent prompt contracts. Precedent "no match" is legitimate -
# it must NOT masquerade as a guidelines/statute gap.
_EMPTY_RISK_FLAG: dict[ResearcherName, str] = {
    "medical_necessity": "no_guidelines_found",
    "legal_researcher": "no_statute_found",
    "policy_detective": "cpb_not_found",
    "precedent_miner": "no_precedent_found",
    "insurer_intelligence": "no_trace_history",
}

# Always-surface procedural angles per domain (text only - NEVER a fabricated
# citation). The Drafter/Strategist read these from ``evidence_gaps``.
_DOMAIN_ANGLE: dict[ResearcherName, str] = {
    "legal_researcher": (
        "Demand full and fair review and document production of the criteria applied "
        "(procedural angle every appeal can lean on)."
    ),
    "policy_detective": (
        "Compare the cited policy criteria against the plan's own medical-necessity "
        "definition for a plan-contradicts-itself angle."
    ),
    "precedent_miner": (
        "Frame any matching external-review decision as persuasive, not binding."
    ),
}


class StubSwarmClient:
    """Deterministic offline swarm client for tests/dry-runs. NOT for benchmarks.

    Produces structurally-valid artifacts so the whole pipeline runs e2e with no
    credentials. Triage fans out to the full routing table for the classified
    denial type (``insurer_intelligence`` always on; ``precedent_miner`` on
    complexity 5), and each ``research()`` has per-domain behavior.
    """

    name = "stub_swarm"

    def triage(self, parsed_case: dict[str, Any]) -> RoutingManifest:
        denial_type = _DENIAL_TYPE_MAP.get(
            parsed_case.get("denial_type", "unknown"), "medical_necessity"
        )
        complexity = estimate_complexity(parsed_case)
        researchers = build_routing(denial_type, complexity)
        return RoutingManifest(
            case_id=parsed_case.get("case_id", "interactive_case"),
            denial_type=denial_type,  # type: ignore[arg-type]
            confidence=0.9,
            complexity_score=complexity,  # type: ignore[arg-type]
            complexity_reasoning=(
                f"stub triage: complexity {complexity}, "
                f"{len(researchers)}-researcher fan-out for {denial_type}"
            ),
            researchers=researchers,
            evidence_quote=parsed_case.get("cited_denial_reason", "")[:160],
            thinking="Deterministic stub classification + routing for offline runs.",
        )

    def research(
        self,
        agent: ResearcherName,
        parsed_case: dict[str, Any],
        depth: ResearchDepth,
        hits: list[CorpusHit],
        phoenix_summary: dict[str, Any] | None = None,
    ) -> ResearchBrief:
        domain = _brief_domain(agent)
        findings = [
            ResearchFinding(
                summary=f"Corpus support: {hit.title}",
                citations=[hit.to_brief_citation()],
            )
            for hit in hits
        ]
        status = "full" if findings else "empty"
        empty_flag = _EMPTY_RISK_FLAG.get(agent, "no_guidelines_found")
        risk_flags = [] if findings else [empty_flag]
        missing = [] if findings else ["No traceable corpus document for this query."]
        # Per-domain procedural angle (text only; never a fabricated citation).
        gaps: list[str] = []
        if agent in _DOMAIN_ANGLE:
            gaps.append(_DOMAIN_ANGLE[agent])
        if agent == "legal_researcher" and parsed_case.get("state", "unknown") in (
            "",
            "unknown",
            None,
        ):
            risk_flags = [*risk_flags, "state_unknown"]
        if agent == "policy_detective" and "plan_document_language" in parsed_case.get(
            "missing_facts", []
        ):
            risk_flags = [*risk_flags, "missing_plan_docs"]
        common = dict(
            case_id=parsed_case.get("case_id", "interactive_case"),
            domain=domain,
            status=status,
            findings=findings,
            missing_evidence=missing,
            evidence_gaps=gaps,
            confidence=0.8 if findings else 0.2,
            thinking=f"Stub {agent} brief over {len(hits)} corpus hit(s).",
        )
        if agent == "insurer_intelligence":
            phoenix = phoenix_summary or {}
            phoenix_status = phoenix.get("status", "unavailable")
            tactic = ""
            insurer_risk = list(risk_flags)
            if phoenix_status in {"disabled", "unavailable"}:
                insurer_risk.append("phoenix_mcp_unavailable")
            else:
                tactic = "Lead with the slice's known winning counter-structure."
            return InsurerBrief(
                **common,  # type: ignore[arg-type]
                agent="insurer_intelligence",
                tactic=tactic,
                success_patterns=list(phoenix.get("success_traits", [])),
                failure_patterns=list(phoenix.get("failure_patterns", [])),
                playbook_version=None,
                similar_trace_count=int(phoenix.get("similar_trace_count", 0)),
                risk_flags=sorted(set(insurer_risk)),
            )
        return ResearchBrief(agent=agent, risk_flags=risk_flags, **common)  # type: ignore[arg-type]

    def strategize(
        self,
        parsed_case: dict[str, Any],
        briefs: list[ResearchBrief],
        manifest: RoutingManifest,
        playbook: dict[str, Any],
    ) -> AppealStrategy:
        all_citations: list[BriefCitation] = [
            c for brief in briefs for c in brief.all_citations()
        ]
        primary = list(dict.fromkeys(c.corpus_doc_id for c in all_citations))[:3]
        domains = list(dict.fromkeys(b.domain for b in briefs))
        # Degraded only when NO researcher produced any traceable finding (an
        # empty precedent brief is a legitimate "no match", not degradation).
        degraded = not any(b.findings for b in briefs)
        insurer = parsed_case.get("insurer", "the insurer")
        service = parsed_case.get("service_or_procedure", "the requested service")
        return AppealStrategy(
            case_id=parsed_case.get("case_id", "interactive_case"),
            archetype="clinical_evidence_led",
            lead_angle=StrategyAngle(
                summary=(
                    f"Rebut {insurer}'s denial of {service} using the documented "
                    f"clinical record and the traceable corpus authorities."
                ),
                primary_citations=primary,
                supporting_brief_refs=domains,
            ),
            letter_outline=[
                LetterOutlineItem(section="intro", content_hint="State the appeal."),
                LetterOutlineItem(
                    section="lead_angle", content_hint="Argue medical necessity."
                ),
                LetterOutlineItem(
                    section="procedural_demands",
                    content_hint="Demand full and fair review.",
                ),
                LetterOutlineItem(section="closing", content_hint="Deadline + disclaimer."),
            ],
            evidence_gaps=[g for b in briefs for g in b.missing_evidence],
            degraded_strategy=degraded,
            playbook_version_used=playbook.get("version"),
            risk_flags=["degraded_strategy"] if degraded else [],
            thinking="Stub strategy: clinical-evidence-led over available briefs.",
        )

    def draft(
        self,
        parsed_case: dict[str, Any],
        strategy: AppealStrategy,
        citations: list[CorpusHit],
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
        critique: AdversarialCritique | None = None,
    ) -> str:
        insurer = parsed_case.get("insurer", "the insurer")
        service = parsed_case.get("service_or_procedure", "the requested service")
        reason = parsed_case.get("cited_denial_reason", "the stated reason")
        cites = "; ".join(
            f"{c.title} ({c.corpus_doc_id})" for c in citations[:3]
        ) or "the documented clinical record"
        revision = ""
        if critique is not None:
            fixes = "; ".join(f.fix for f in critique.findings if f.fix)
            revision = f" Revision addressing prior review: {fixes}" if fixes else ""
        return (
            f"To the appeals reviewer: I write to appeal {insurer}'s denial of "
            f"{service}. The denial rests on: {reason}. {strategy.lead_angle.summary} "
            f"Supporting authorities: {cites}. I request a full and fair review by a "
            f"qualified reviewer who was not previously consulted on this claim, and a "
            f"decision within the applicable deadline.{revision}\n\n{_DISCLAIMER}"
        )

    def critique(
        self,
        parsed_case: dict[str, Any],
        strategy: AppealStrategy,
        letter: str,
        iteration: int = 1,
    ) -> AdversarialCritique:
        findings: list[CritiqueFinding] = []
        if _DISCLAIMER.lower() not in letter.lower():
            findings.append(
                CritiqueFinding(
                    issue="Mandatory disclaimer missing.",
                    severity=0.95,
                    fix=f"Append verbatim: {_DISCLAIMER}",
                    category="disclaimer_issue",
                )
            )
        else:
            findings.append(
                CritiqueFinding(
                    issue="Citations could be more specific.",
                    severity=0.2,
                    fix="Add section numbers where available.",
                    category="citation_precision",
                )
            )
        overall = max((f.severity for f in findings), default=0.0)
        return AdversarialCritique(
            case_id=parsed_case.get("case_id", "interactive_case"),
            iteration=iteration,  # type: ignore[arg-type]
            findings=findings,
            overall_severity=overall,
            passes=overall < 0.6,
            thinking="Stub adversarial review: disclaimer + citation-precision check.",
        )


# --- Gemini (live; constructed offline, generated in a GCP session) ----------


class GeminiSwarmClient:
    """Vertex/Gemini-backed swarm client. Each method loads its role prompt from
    the registry and calls Gemini with a structured response schema. On any
    failure it falls back to a weak, structurally-valid artifact (mirroring the
    Part A clients) so the pipeline never crashes mid-run.

    Construction/config is unit-tested offline; live generation is exercised in a
    GCP integration session (Phase 4)."""

    name = "gemini_swarm"

    def __init__(self, model: str | None = None, location: str = "global") -> None:
        self.model = model or os.environ.get("AEGIS_SWARM_MODEL", "gemini-3.1-pro")
        self.location = location
        self._fallback = StubSwarmClient()

    def _generate_json(self, role: str, schema: type, context: dict[str, Any]) -> Any:
        """Load ``role``'s prompt, send prompt + context JSON, parse into ``schema``."""
        import json

        from google import genai
        from google.genai import types

        from app.aegis_swarm.prompts.registry import load_prompt

        prompt = load_prompt(role)
        contents = f"{prompt}\n\nCONTEXT JSON:\n{json.dumps(context, default=str)}"
        client = genai.Client(vertexai=True, location=self.location)
        response = client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.3,
            ),
        )
        return schema.model_validate_json(response.text)

    def triage(self, parsed_case: dict[str, Any]) -> RoutingManifest:
        try:
            return self._generate_json("triage", RoutingManifest, {"case": parsed_case})
        except Exception:
            _LOG.warning("GeminiSwarmClient.triage failed; using stub", exc_info=True)
            return self._fallback.triage(parsed_case)

    def research(
        self,
        agent: ResearcherName,
        parsed_case: dict[str, Any],
        depth: ResearchDepth,
        hits: list[CorpusHit],
        phoenix_summary: dict[str, Any] | None = None,
    ) -> ResearchBrief:
        schema = InsurerBrief if agent == "insurer_intelligence" else ResearchBrief
        try:
            return self._generate_json(
                agent,
                schema,
                {
                    "case": parsed_case,
                    "depth": depth,
                    "corpus_hits": [h.model_dump() for h in hits],
                    "phoenix_summary": phoenix_summary or {},
                },
            )
        except Exception:
            _LOG.warning(
                "GeminiSwarmClient.research(%s) failed; using stub", agent, exc_info=True
            )
            return self._fallback.research(agent, parsed_case, depth, hits, phoenix_summary)

    def strategize(
        self,
        parsed_case: dict[str, Any],
        briefs: list[ResearchBrief],
        manifest: RoutingManifest,
        playbook: dict[str, Any],
    ) -> AppealStrategy:
        try:
            return self._generate_json(
                "strategist",
                AppealStrategy,
                {
                    "case": parsed_case,
                    "briefs": [b.model_dump() for b in briefs],
                    "manifest": manifest.model_dump(),
                    "playbook": playbook,
                },
            )
        except Exception:
            _LOG.warning("GeminiSwarmClient.strategize failed; using stub", exc_info=True)
            return self._fallback.strategize(parsed_case, briefs, manifest, playbook)

    def draft(
        self,
        parsed_case: dict[str, Any],
        strategy: AppealStrategy,
        citations: list[CorpusHit],
        playbook: dict[str, Any],
        phoenix_summary: dict[str, Any],
        critique: AdversarialCritique | None = None,
    ) -> str:
        import json

        try:
            from google import genai
            from google.genai import types

            from app.aegis_swarm.prompts.registry import load_prompt

            context = {
                "case": parsed_case,
                "strategy": strategy.model_dump(),
                "citations": [c.model_dump() for c in citations],
                "playbook": playbook,
                "critique": critique.model_dump() if critique else None,
            }
            contents = f"{load_prompt('drafter')}\n\nCONTEXT JSON:\n{json.dumps(context, default=str)}"
            client = genai.Client(vertexai=True, location=self.location)
            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.3),
            )
            return response.text or ""
        except Exception:
            _LOG.warning("GeminiSwarmClient.draft failed; using stub", exc_info=True)
            return self._fallback.draft(
                parsed_case, strategy, citations, playbook, phoenix_summary, critique
            )

    def critique(
        self,
        parsed_case: dict[str, Any],
        strategy: AppealStrategy,
        letter: str,
        iteration: int = 1,
    ) -> AdversarialCritique:
        try:
            return self._generate_json(
                "adversarial_reviewer",
                AdversarialCritique,
                {
                    "case": parsed_case,
                    "strategy": strategy.model_dump(),
                    "letter": letter,
                    "iteration": iteration,
                },
            )
        except Exception:
            _LOG.warning("GeminiSwarmClient.critique failed; using stub", exc_info=True)
            return self._fallback.critique(parsed_case, strategy, letter, iteration)
