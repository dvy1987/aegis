"""Pure swarm pipeline (offline-capable walking skeleton).

Wires the thin vertical slice end to end:

    Triage -> researcher(s) -> Strategist -> Drafter -> Adversarial Reviewer
            -> self_check -> AppealPackage (+ SwarmRunArtifacts sidecar)

Mirrors ``aegis_v1/pipeline.py``: deterministic glue here, LLM reasoning behind
the injectable ``SwarmAgentClient``. The terminal artifact REUSES Part A's
``AppealPackage`` (so the judge panel, simulator, recorder, and firewall work
unchanged); swarm-internal outputs ride along as ``SwarmRunArtifacts``.

The Outcome Simulator is NOT run here - it lives in the orchestration/eval layer
(``swarm_orchestrator.py``), preserving Part A's separation of powers (D11).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from app.aegis_swarm.corpus_store import CorpusHit, CorpusStore, LocalCorpusStore
from app.aegis_swarm.prompts.registry import current_version
from app.aegis_swarm.schemas import (
    AdversarialCritique,
    AgentTraceSignal,
    InsurerBrief,
    ResearchBrief,
    SwarmRunArtifacts,
)
from app.aegis_swarm.tools import (
    RESEARCHER_DOMAIN,
    build_research_query,
    corpus_search_with_discovery,
    depth_to_top_k,
    get_learned_playbook,
    make_agent_trace_signal,
    swarm_phoenix_lookup,
)

if TYPE_CHECKING:
    from app.aegis_swarm.literature_discovery import LiteratureDiscovery
    from app.aegis_swarm.trace_recorder import SwarmTraceRecorder
from app.aegis_v1.guardrails import apply_guardrails
from app.aegis_v1.schemas import (
    AppealDraft,
    AppealPackage,
    CitationHit,
    RetrievalResult,
    TraceMetadata,
)
from app.aegis_v1.tools import DISCLAIMER, case_parser, self_check

if TYPE_CHECKING:
    from app.aegis_swarm.client import SwarmAgentClient

RunMode = Literal["interactive", "benchmark", "autonomous_promotion"]
_LOOP_THRESHOLD = 0.6  # adversarial overall_severity that triggers one redraft


def _corpus_hits_to_citations(hits: list[CorpusHit]) -> list[CitationHit]:
    """Map swarm CorpusHits onto Part A CitationHits (same fields) so the reused
    ``self_check`` and ``AppealDraft`` see the swarm's traceable citations."""
    seen: dict[str, CitationHit] = {}
    for hit in hits:
        if hit.corpus_doc_id not in seen:
            seen[hit.corpus_doc_id] = CitationHit(
                corpus_doc_id=hit.corpus_doc_id,
                title=hit.title,
                quote=hit.quote,
                relevance_score=hit.relevance_score,
            )
    return list(seen.values())


def _assemble_draft(
    parsed: dict[str, Any],
    strategy,
    letter_body: str,
    citations: list[CitationHit],
    playbook: dict[str, Any],
    extra_risk_flags: list[str],
) -> AppealDraft:
    """Deterministically wrap the LLM letter prose into an AppealDraft, applying
    the same guardrails + citation discipline as Part A's ``draft_appeal``."""
    allowed_doc_ids = {c.corpus_doc_id for c in citations}
    letter = apply_guardrails(letter_body, allowed_doc_ids=allowed_doc_ids)
    evidence_items = list(
        dict.fromkeys(
            [e.item for e in strategy.evidence_checklist_for_drafter]
            + parsed.get("missing_facts", [])
            + playbook.get("required_evidence", [])
        )
    )
    risk_flags = sorted(
        set(
            extra_risk_flags
            + list(strategy.risk_flags)
            + list(playbook.get("risk_flags", []))
            + ([] if citations else ["no_corpus_citations"])
        )
    )
    return AppealDraft(
        case_summary=(
            f"{parsed.get('insurer', 'the insurer')} denied "
            f"{parsed.get('service_or_procedure', 'the requested service')} for "
            f"{parsed.get('diagnosis_summary', 'the documented condition')}."
        ),
        denial_grounds_interpreted=parsed.get("cited_denial_reason", ""),
        appeal_strategy=strategy.lead_angle.summary,
        appeal_letter=letter,
        citations_used=citations[:5],
        missing_evidence_checklist=evidence_items,
        risk_flags=risk_flags,
        safety_disclaimer=DISCLAIMER,
    )


def _build_trace_signals(
    manifest,
    briefs: list[ResearchBrief],
    strategy,
    critiques: list[AdversarialCritique],
    draft: AppealDraft,
    drafter_iterations: int,
    disclaimer_present: bool,
) -> list[AgentTraceSignal]:
    """Emit one firewall-safe signal per invoked agent (FR-5). Summaries are
    built from safe primitives ONLY (enums + counts) - never letter text, brief
    quotes, agent ``thinking``, or PHI."""
    signals: list[AgentTraceSignal] = [
        make_agent_trace_signal(
            "triage",
            status=manifest.denial_type,
            finding_count=len(manifest.invoked()),
            risk_flags=list(manifest.risk_flags),
            summary=(
                f"classified {manifest.denial_type} (complexity "
                f"{manifest.complexity_score}); {len(manifest.invoked())}-researcher fan-out"
            ),
        )
    ]
    for brief in briefs:
        signals.append(
            make_agent_trace_signal(
                brief.agent,
                status=brief.status,
                finding_count=len(brief.findings),
                citation_count=len(brief.all_citations()),
                risk_flags=list(brief.risk_flags),
                summary=f"{brief.domain} brief: {brief.status}, {len(brief.findings)} finding(s)",
            )
        )
    if strategy is not None:
        signals.append(
            make_agent_trace_signal(
                "strategist",
                status="degraded" if strategy.degraded_strategy else "ok",
                citation_count=len(strategy.all_citations()),
                risk_flags=list(strategy.risk_flags),
                summary=(
                    f"archetype {strategy.archetype}; {len(strategy.all_citations())} "
                    f"citation(s); {len(strategy.evidence_checklist_for_drafter)} evidence item(s)"
                ),
            )
        )
    signals.append(
        make_agent_trace_signal(
            "drafter",
            status=f"drafted_iter_{drafter_iterations}",
            citation_count=len(draft.citations_used),
            risk_flags=list(draft.risk_flags),
            summary=(
                f"letter drafted in {drafter_iterations} iteration(s); "
                f"{len(draft.citations_used)} citation(s); disclaimer={disclaimer_present}"
            ),
        )
    )
    if critiques:
        last = critiques[-1]
        signals.append(
            make_agent_trace_signal(
                "adversarial_reviewer",
                status="passes" if last.passes else "flagged",
                finding_count=len(last.findings),
                risk_flags=list(last.risk_flags),
                summary=(
                    f"review iteration {last.iteration}: severity {last.overall_severity}; "
                    f"passes={last.passes}; {len(last.findings)} finding(s)"
                ),
            )
        )
    return signals


def run_swarm_pipeline(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
    dataset_split: str = "interactive",
    run_mode: RunMode = "interactive",
    client: "SwarmAgentClient | None" = None,
    corpus_store: CorpusStore | None = None,
    discovery: "LiteratureDiscovery | None" = None,
    trace_recorder: "SwarmTraceRecorder | None" = None,
) -> dict[str, Any]:
    """Run the swarm Student flow and return ``{"appeal_package", "artifacts"}``.

    Defaults to the offline ``StubSwarmClient`` + ``LocalCorpusStore`` so the
    full slice runs with no credentials. Live runs inject ``GeminiSwarmClient``.
    """
    from app.aegis_swarm.client import StubSwarmClient

    active = client or StubSwarmClient()
    store = corpus_store or LocalCorpusStore()

    parsed = case_parser(
        denial_text=denial_text,
        clinical_context=clinical_context,
        case_id=case_id,
    )
    # Playbook + Phoenix lookups use Part A's normalized denial_type (playbooks
    # are keyed that way); the manifest carries the swarm's classification.
    insurer = parsed["insurer"]
    pa_denial_type = parsed["denial_type"]
    phoenix = swarm_phoenix_lookup(insurer, pa_denial_type, parsed["case_id"])
    playbook = get_learned_playbook(insurer, pa_denial_type)

    manifest = active.triage(parsed)

    briefs: list[ResearchBrief] = []
    insurer_brief: InsurerBrief | None = None
    all_hits: list[CorpusHit] = []
    discovery_runs: list[dict[str, Any]] = []
    query = build_research_query(parsed)
    for inv in manifest.researchers:
        if not inv.invoke:
            continue
        domain = RESEARCHER_DOMAIN[inv.name]
        hits, disc = corpus_search_with_discovery(
            store,
            domain,
            query,
            top_k=depth_to_top_k(inv.depth),
            case_id=case_id,
            discovery=discovery,
        )
        if disc is not None:
            discovery_runs.append(disc)
        all_hits.extend(hits)
        brief = active.research(inv.name, parsed, inv.depth, hits, phoenix_summary=phoenix)
        if isinstance(brief, InsurerBrief):
            insurer_brief = brief
        briefs.append(brief)

    strategy = active.strategize(parsed, briefs, manifest, playbook)

    citations = _corpus_hits_to_citations(all_hits)

    letter = active.draft(parsed, strategy, all_hits, playbook, phoenix)
    critiques: list[AdversarialCritique] = [
        active.critique(parsed, strategy, letter, iteration=1)
    ]
    drafter_iterations = 1
    if critiques[0].overall_severity >= _LOOP_THRESHOLD:
        letter = active.draft(
            parsed, strategy, all_hits, playbook, phoenix, critique=critiques[0]
        )
        drafter_iterations = 2
        critiques.append(active.critique(parsed, strategy, letter, iteration=2))

    extra_risk_flags = list(
        dict.fromkeys(
            [f for f in phoenix.get("risk_flags", []) if not f.startswith("case_id:")]
        )
    )
    draft = _assemble_draft(
        parsed, strategy, letter, citations, playbook, extra_risk_flags
    )

    retrieval_results = RetrievalResult(
        query=query, hits=citations
    ).model_dump()
    check = self_check(
        parsed_case=parsed,
        appeal_draft=draft.model_dump(),
        retrieval_results=retrieval_results,
    )

    invoked_roles = ["triage", *manifest.invoked(), "strategist", "drafter", "adversarial_reviewer"]
    agent_versions = {role: current_version(role) for role in dict.fromkeys(invoked_roles)}

    run_risk_flags = sorted(
        set(
            draft.risk_flags
            + check.get("risk_flags", [])
            + list(manifest.risk_flags)
            + [rf for b in briefs for rf in b.risk_flags]
            + [rf for c in critiques for rf in c.risk_flags]
        )
    )

    package = AppealPackage(
        run_id=f"aegis-swarm-{uuid4().hex[:8]}",
        parsed_case=parsed,
        appeal_package_draft=draft.model_dump(),
        self_check=check,
        risk_flags=run_risk_flags,
        trace_metadata=TraceMetadata(
            case_id=parsed["case_id"],
            insurer=insurer,
            denial_type=manifest.denial_type,
            plan_type=parsed["plan_type"],
            state=parsed["state"],
            prompt_version="aegis_swarm_v1",
            playbook_version=playbook.get("version", "cold-start"),
            dataset_split=dataset_split,
            run_mode=run_mode,
        ),
    )

    trace_signals = _build_trace_signals(
        manifest,
        briefs,
        strategy,
        critiques,
        draft,
        drafter_iterations,
        disclaimer_present=bool(
            check.get("safety_check", {}).get("disclaimer_present", False)
        ),
    )

    artifacts = SwarmRunArtifacts(
        routing_manifest=manifest,
        briefs=briefs,
        insurer_brief=insurer_brief,
        strategy=strategy,
        critiques=critiques,
        drafter_iterations=drafter_iterations,
        agent_versions=agent_versions,
        agent_trace_signals=trace_signals,
        risk_flags=run_risk_flags,
    )

    active_recorder = trace_recorder
    if active_recorder is not None:
        active_recorder.record_agent_signals(
            package.run_id,
            trace_signals,
            package.trace_metadata.model_dump(),
        )

    payload = {
        "appeal_package": package.model_dump(),
        "artifacts": artifacts.model_dump(),
    }
    if discovery_runs:
        payload["discovery_runs"] = discovery_runs
    return payload
