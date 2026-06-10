from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

from app.aegis_v1.schemas import (
    AppealDraft,
    CitationHit,
    ParsedCase,
    PhoenixSummary,
    Playbook,
    RetrievalResult,
    SelfCheckResult,
)

DISCLAIMER = "Not legal or medical advice. Draft assistance only."

BACKEND_ROOT = Path(os.environ.get("AEGIS_BACKEND_ROOT", Path(__file__).resolve().parents[2]))
REPO_ROOT = Path(os.environ.get("AEGIS_REPO_ROOT", BACKEND_ROOT.parent))
CORPUS_DIR = BACKEND_ROOT / "corpus"
PLAYBOOK_DIR = REPO_ROOT / "playbooks"

_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*")
_PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\bMRN\s*#?:?\s*\w+\b", re.IGNORECASE),
]


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD_RE.finditer(text)]


def _normalize_denial_type(text: str) -> str:
    lowered = " ".join(text.lower().split())
    if any(term in lowered for term in ("prior authorization", "preauthorization")):
        return "prior_authorization"
    if "peer-to-peer" in lowered or "peer to peer" in lowered:
        return "prior_authorization"
    if "medical necessity" in lowered or "medically necessary" in lowered:
        return "medical_necessity"
    if "not a covered service" in lowered or "excluded benefit" in lowered:
        return "coverage_exclusion"
    return "unknown"


def _detect_insurer(text: str) -> str:
    lowered = text.lower()
    if "aetna" in lowered:
        return "Aetna"
    if "cigna" in lowered:
        return "Cigna"
    if "unitedhealthcare" in lowered or "united healthcare" in lowered:
        return "UnitedHealthcare"
    if re.search(r"\buhc\b", lowered):
        return "UnitedHealthcare"
    return "unknown"


def _detect_plan_type(text: str) -> str:
    lowered = text.lower()
    if "medicare" in lowered or "medicaid" in lowered:
        return "out_of_scope"
    return "commercial"


def _first_match(patterns: list[str], text: str, default: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            value = " ".join(match.group(1).split())
            return value.strip(" .,:;")
    return default


def _reason_sentence(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    reason_terms = (
        "denied",
        "denying",
        "not medically necessary",
        "medical necessity",
        "prior authorization",
        "does not show",
    )
    for sentence in sentences:
        if any(term in sentence.lower() for term in reason_terms):
            return " ".join(sentence.split())
    return "Denial reason not explicit in the supplied text."


def _title_for(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return fallback


def _best_quote(text: str, query_tokens: set[str]) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return text[:350].strip()
    best = max(
        paragraphs,
        key=lambda paragraph: len(set(_tokenize(paragraph)) & query_tokens),
    )
    return " ".join(best.split())[:700]


def _load_corpus() -> list[tuple[Path, str]]:
    # rglob: the corpus is now organized into domain subdirs (clinical/legal/
    # precedent/insurer) for the Part B swarm; Part A retrieves over the union.
    if not CORPUS_DIR.exists():
        return []
    return [
        (path, path.read_text(encoding="utf-8"))
        for path in sorted(CORPUS_DIR.rglob("*.md"))
    ]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def case_parser(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
    *,
    insurer: str | None = None,
    patient_age: int | None = None,
    patient_gender: str | None = None,
) -> dict[str, Any]:
    """Parse a synthetic health-insurance denial into the MVP CaseJSON fields."""

    from app.aegis_v1.patient_context import (
        format_patient_clinical_context,
        normalize_gender,
        normalize_insurer,
    )

    structured = (
        insurer is not None
        and patient_age is not None
        and patient_gender is not None
    )
    if structured:
        resolved_insurer = normalize_insurer(insurer)
        resolved_gender = normalize_gender(patient_gender)
        if not clinical_context.strip():
            clinical_context = format_patient_clinical_context(
                patient_age=patient_age,
                patient_gender=resolved_gender,
            )
        full_text = denial_text.strip()
    else:
        resolved_insurer = None
        resolved_gender = ""
        full_text = f"{denial_text}\n{clinical_context}".strip()
    deadlines = sorted(set(re.findall(r"\b\d+\s+days\b", full_text, re.IGNORECASE)))
    diagnosis = _first_match(
        [
            r"diagnosis(?:\s+of)?\s+([A-Za-z0-9 ,()/+-]+?)(?:\.|,|\n|$)",
            r"for\s+(severe\s+[A-Za-z0-9 ,()/+-]+?)(?:\.|,|\n|$)",
            r"has\s+([A-Za-z0-9 ,()/+-]+?)(?:,|\s+and|\.)",
        ],
        full_text,
        "Diagnosis not clearly stated.",
    )
    service = _first_match(
        [
            r"request(?:ed)?\s+(?:from your provider\s+)?for\s+([A-Za-z0-9 ,()/+-]+?)(?:\.|,|\n| from | on )",
            r"coverage\s+for\s+([A-Za-z0-9 ,()/+-]+?)(?:\.|,|\n|$)",
            r"denial\s+of\s+coverage\s+for\s+([A-Za-z0-9 ,()/+-]+?)(?:\.|,|\n|$)",
        ],
        full_text,
        "Requested service not clearly stated.",
    )

    missing_facts: list[str] = []
    if structured:
        if resolved_insurer == "unknown":
            missing_facts.append("insurer_name")
        if patient_age is None or patient_age < 1:
            missing_facts.append("patient_age")
        if not resolved_gender:
            missing_facts.append("patient_gender")
    else:
        if _detect_insurer(full_text) == "unknown":
            missing_facts.append("insurer_name")
        if not clinical_context:
            missing_facts.append("clinical_context")
    if diagnosis == "Diagnosis not clearly stated.":
        missing_facts.append("diagnosis")
    if service == "Requested service not clearly stated.":
        missing_facts.append("service_or_procedure")
    if "plan" not in full_text.lower():
        missing_facts.append("plan_document_language")

    parsed = ParsedCase(
        case_id=case_id or "interactive_case",
        insurer=resolved_insurer if structured else _detect_insurer(full_text),
        denial_type=_normalize_denial_type(full_text),
        plan_type=_detect_plan_type(full_text),
        service_or_procedure=service,
        diagnosis_summary=diagnosis,
        state="unknown",
        cited_denial_reason=_reason_sentence(denial_text),
        deadlines_mentioned=deadlines,
        missing_facts=missing_facts,
        denial_text=denial_text,
        clinical_context=clinical_context,
        patient_age=patient_age if structured else None,
        patient_gender=resolved_gender if structured else "",
    )
    return parsed.model_dump()


def corpus_retrieval(query: str, top_k: int = 3) -> dict[str, Any]:
    """Retrieve traceable local-corpus citations with BM25 over markdown files.

    When the orchestrator sets a controlled retrieval (cloud + planner path), the
    model-supplied ``query`` is ignored and the pre-flight result is returned.
    """
    from app.aegis_v1.retrieval_context import get_controlled_retrieval

    controlled = get_controlled_retrieval()
    if controlled is not None:
        return controlled

    documents = _load_corpus()
    if not documents:
        return RetrievalResult(query=query, hits=[]).model_dump()

    tokenized = [_tokenize(content) for _, content in documents]
    bm25 = BM25Okapi(tokenized)
    query_tokens = _tokenize(query)
    scores = bm25.get_scores(query_tokens)
    ranked = sorted(
        zip(documents, scores, strict=True),
        key=lambda item: float(item[1]),
        reverse=True,
    )

    hits = []
    query_token_set = set(query_tokens)
    for (path, content), score in ranked[: max(1, min(top_k, len(ranked)))]:
        hits.append(
            CitationHit(
                corpus_doc_id=path.name,
                title=_title_for(content, path.stem.replace("_", " ").title()),
                quote=_best_quote(content, query_token_set),
                relevance_score=round(float(score), 4),
            )
        )
    return RetrievalResult(query=query, hits=hits).model_dump()


def playbook_loader(
    insurer: str,
    denial_type: str,
    *,
    sub_tactic: str | None = None,
) -> dict[str, Any]:
    """Load the current promoted playbook, or return a marked cold-start playbook."""

    from app.learning.slice_key import playbook_filename

    normalized_type = _normalize_denial_type(denial_type.replace("_", " "))
    if normalized_type == "unknown":
        normalized_type = _slug(denial_type)
    tactic = (sub_tactic or "unknown").strip()
    specific_path = PLAYBOOK_DIR / playbook_filename(insurer, normalized_type, tactic)
    legacy_path = PLAYBOOK_DIR / f"{_slug(insurer)}__{normalized_type}.json"
    path = specific_path if specific_path.exists() else legacy_path

    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        playbook = Playbook(
            insurer=data.get("insurer", insurer),
            denial_type=data.get("denial_type", normalized_type),
            version=data.get("version", "unknown"),
            status="loaded",
            tactics=data.get("tactics", []),
            required_evidence=data.get("required_evidence", []),
            risk_flags=data.get("risk_flags", []),
        )
        return playbook.model_dump()

    if normalized_type == "prior_authorization":
        tactics = [
            "Show the requested service meets the policy criteria.",
            "Explain any peer-to-peer or scheduling failure factually.",
            "Ask for reconsideration using records already submitted.",
        ]
        required_evidence = [
            "provider letter",
            "prior treatment history",
            "authorization request record",
        ]
    else:
        tactics = [
            "Rebut the medical-necessity rationale with documented severity.",
            "Tie symptoms and failed lower-level care to the requested service.",
            "Request full and fair review by an appropriately qualified reviewer.",
        ]
        required_evidence = [
            "clinical notes",
            "prior treatment failures",
            "guideline or plan-language support",
        ]

    return Playbook(
        insurer=insurer,
        denial_type=normalized_type,
        version="cold-start",
        status="missing",
        tactics=tactics,
        required_evidence=required_evidence,
        risk_flags=["playbook_cold_start"],
    ).model_dump()


def insurer_playbook_bundle(insurer: str) -> dict[str, Any]:
    """Load EVERY promoted playbook for an insurer (question-agent prep).

    On a real appeal the denial type is NOT knowable a priori (it is parsed
    metadata, stripped from what the Student sees), so the question agent gets
    the complete insurer bundle and must reason across all of it instead of
    being handed the answer via a denial-type-filtered playbook.
    """
    playbooks: list[dict[str, Any]] = []
    prefix = f"{_slug(insurer)}__"
    if PLAYBOOK_DIR.exists():
        for path in sorted(PLAYBOOK_DIR.glob(f"{prefix}*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            playbooks.append(
                Playbook(
                    insurer=data.get("insurer", insurer),
                    denial_type=data.get("denial_type", "unknown"),
                    version=data.get("version", "unknown"),
                    status="loaded",
                    tactics=data.get("tactics", []),
                    required_evidence=data.get("required_evidence", []),
                    risk_flags=data.get("risk_flags", []),
                ).model_dump()
            )
    if not playbooks:
        # Cold start: generic playbook, explicitly NOT denial-type-specific.
        playbooks.append(playbook_loader(insurer, "unknown"))
    return {"insurer": insurer, "playbooks": playbooks, "count": len(playbooks)}


_LAUNDERED_FORBIDDEN = (
    "expected_appeal_vectors",
    "exploitable_weaknesses",
    "strong_defenses",
    "matrix_cell",
    "denial_pattern_sources",
)


def _summarize_traces(
    traces: list[dict[str, Any]],
    *,
    insurer: str,
    denial_type: str,
    query: str,
) -> PhoenixSummary:
    """Pure transform: laundered trace dicts -> PhoenixSummary.

    Reads ONLY the laundered annotation fields (`dimensions[<name>].score` and
    `.improvement`). Teacher-only answer-key fields are stripped defensively
    even if a malformed trace ever rides one along (INV-2).
    """
    if not traces:
        return PhoenixSummary(
            status="cold_start",
            query=query,
            similar_trace_count=0,
            failure_patterns=[
                "No promoted Phoenix trace pattern is available for this slice yet."
            ],
            success_traits=[
                "Use local corpus citations and clearly mark missing evidence."
            ],
            risk_flags=["phoenix_mcp_cold_start"],
        )

    failure_patterns: list[str] = []
    success_traits: list[str] = []
    for trace in traces:
        dims = trace.get("dimensions") or {}
        if not isinstance(dims, dict):
            continue
        for dim_name, record in dims.items():
            if not isinstance(record, dict):
                continue
            score = record.get("score")
            improvement = (record.get("improvement") or "").strip()
            if any(forbidden in dim_name for forbidden in _LAUNDERED_FORBIDDEN):
                continue
            if score == 1 and improvement:
                failure_patterns.append(improvement)
            elif score == 5:
                success_traits.append(f"strong {dim_name}")

    failure_patterns = list(dict.fromkeys(failure_patterns))[:5]
    success_traits = list(dict.fromkeys(success_traits))[:5]
    return PhoenixSummary(
        status="available",
        query=query,
        similar_trace_count=len(traces),
        failure_patterns=failure_patterns,
        success_traits=success_traits,
        risk_flags=["phoenix_mcp_live"],
    )


def phoenix_mcp_lookup(
    insurer: str,
    denial_type: str,
    case_id: str = "interactive_case",
) -> dict[str, Any]:
    """Return Phoenix-memory context for a slice. T4.1 wires this to live MCP
    traces; the disabled/cold_start fallbacks remain so the MCP-off
    counterfactual demo (`PHOENIX_MCP_ENABLED=false`) still works."""

    normalized_type = _normalize_denial_type(denial_type.replace("_", " "))
    if normalized_type == "unknown":
        normalized_type = _slug(denial_type)
    project = os.environ.get("PHOENIX_PROJECT_NAME", "default")
    query = (
        f"traces where project='{project}' "
        f"and insurer='{insurer}' and denial_type='{normalized_type}'"
    )

    if os.getenv("PHOENIX_MCP_ENABLED", "true").lower() in {"0", "false", "no"}:
        return PhoenixSummary(
            status="disabled",
            query=query,
            risk_flags=["phoenix_mcp_disabled"],
        ).model_dump()

    try:
        from app.aegis_v1.phoenix_mcp import fetch_slice_traces

        traces = fetch_slice_traces(
            insurer=insurer,
            denial_type=normalized_type,
            project=project,
            limit=20,
        )
    except Exception:
        traces = []

    summary = _summarize_traces(
        traces, insurer=insurer, denial_type=normalized_type, query=query
    )
    if summary.status == "cold_start":
        summary.risk_flags = ["phoenix_mcp_cold_start", f"case_id:{case_id}"]
    return summary.model_dump()


def drafter(
    parsed_case: dict[str, Any],
    retrieval_results: dict[str, Any],
    playbook: dict[str, Any],
    phoenix_summary: dict[str, Any],
) -> dict[str, Any]:
    """ADK Student tool: draft the appeal package.

    This is the LLM-facing tool registered on the agent, so its signature exposes
    ONLY the data parameters the model fills — deliberately no dependency-injection
    seam. A `client: "DrafterLLMClient | None"` param here would (a) make ADK's
    tool-schema builder call `typing.get_type_hints()` on a forward ref it cannot
    resolve (the type is imported lazily inside the body) and crash agent setup,
    and (b) leak an internal type into the model's function declaration. The drafter
    LLM client is injected only by the orchestration/eval layer via `draft_appeal()`;
    the live agent path uses the default GeminiDrafterClient.
    """
    return draft_appeal(parsed_case, retrieval_results, playbook, phoenix_summary)


def draft_appeal(
    parsed_case: dict[str, Any],
    retrieval_results: dict[str, Any],
    playbook: dict[str, Any],
    phoenix_summary: dict[str, Any],
    client: Any | None = None,
    prompt_version: str | None = None,
    prompt_text: str | None = None,
) -> dict[str, Any]:
    """Injectable drafter core. The letter PROSE is produced by an evolvable LLM
    (or offline stub); structure, citations, and safety are deterministic. Tests
    and the deterministic pipeline pass `client`; ADK calls the thin `drafter()`
    wrapper instead so the DI seam never reaches the model's tool schema."""

    from app.aegis_v1.drafter_client import (
        DrafterLLMClient,
        GeminiDrafterClient,
        get_active_drafter_prompt_version,
        load_drafter_prompt,
    )
    from app.aegis_v1.guardrails import apply_guardrails

    case = ParsedCase.model_validate(parsed_case)
    retrieval = RetrievalResult.model_validate(retrieval_results)
    loaded_playbook = Playbook.model_validate(playbook)
    phoenix = PhoenixSummary.model_validate(phoenix_summary)
    citations = retrieval.hits[:3]

    active: DrafterLLMClient = client or GeminiDrafterClient()
    active_prompt_version = prompt_version or get_active_drafter_prompt_version()
    resolved_prompt = prompt_text if prompt_text is not None else load_drafter_prompt(active_prompt_version)
    raw_body = active.draft(
        # Default is the current promoted prompt. Eval/showcase can override it to
        # produce a real before/after on the same case.
        prompt=resolved_prompt,
        parsed_case=case.model_dump(),
        citations=[c.model_dump() for c in citations],
        playbook=loaded_playbook.model_dump(),
        phoenix_summary=phoenix.model_dump(),
    )
    allowed_doc_ids = {hit.corpus_doc_id for hit in citations}
    letter = apply_guardrails(raw_body, allowed_doc_ids=allowed_doc_ids)

    evidence_items = list(
        dict.fromkeys(case.missing_facts + loaded_playbook.required_evidence)
    )
    tactic_text = " ".join(loaded_playbook.tactics[:2])

    risk_flags = []
    if active_prompt_version in {"drafter_v1", "drafter_v1_weak", "drafter_v1_weak.md"}:
        risk_flags.append("weak_prompt_v1")
    else:
        risk_flags.append(f"prompt:{active_prompt_version}")
    risk_flags.extend(loaded_playbook.risk_flags)
    risk_flags.extend(
        flag for flag in phoenix.risk_flags if not flag.startswith("case_id:")
    )
    if not citations:
        risk_flags.append("no_corpus_citations")

    draft = AppealDraft(
        case_summary=(
            f"{case.insurer} denied {case.service_or_procedure} for "
            f"{case.diagnosis_summary}."
        ),
        denial_grounds_interpreted=case.cited_denial_reason,
        appeal_strategy=tactic_text or "Use a conservative medical-record appeal.",
        appeal_letter=letter,
        citations_used=citations,
        missing_evidence_checklist=evidence_items,
        risk_flags=sorted(set(risk_flags)),
        safety_disclaimer=DISCLAIMER,
    )
    return draft.model_dump()


def self_check(
    parsed_case: dict[str, Any],
    appeal_draft: dict[str, Any],
    retrieval_results: dict[str, Any],
) -> dict[str, Any]:
    """Verify disclaimer, traceable citations, basic fact consistency, and PHI."""

    case = ParsedCase.model_validate(parsed_case)
    draft = AppealDraft.model_validate(appeal_draft)
    retrieval = RetrievalResult.model_validate(retrieval_results)
    available_doc_ids = {hit.corpus_doc_id for hit in retrieval.hits}
    cited_doc_ids = [hit.corpus_doc_id for hit in draft.citations_used]
    untraceable = [doc_id for doc_id in cited_doc_ids if doc_id not in available_doc_ids]
    letter_lower = draft.appeal_letter.lower()

    disclaimer_ok = DISCLAIMER.lower() in letter_lower
    pii_hits = [
        pattern.pattern for pattern in _PII_PATTERNS if pattern.search(draft.appeal_letter)
    ]
    fact_flags = {
        "insurer_mentioned": case.insurer == "unknown"
        or case.insurer.lower() in letter_lower,
        "service_mentioned": case.service_or_procedure.lower() in letter_lower,
        "denial_reason_mentioned": bool(case.cited_denial_reason),
    }
    risk_flags = list(draft.risk_flags)
    if untraceable:
        risk_flags.append("untraceable_citation")
    if not disclaimer_ok:
        risk_flags.append("missing_disclaimer")
    if pii_hits:
        risk_flags.append("potential_pii")

    result = SelfCheckResult(
        hard_gate_pass=not untraceable and disclaimer_ok and not pii_hits,
        citation_check={
            "all_citations_traceable": not untraceable,
            "checked_corpus_doc_ids": cited_doc_ids,
            "untraceable_citations": untraceable,
        },
        fact_check=fact_flags,
        safety_check={
            "disclaimer_present": disclaimer_ok,
            "pii_patterns_detected": pii_hits,
            "no_guarantee_language": not any(
                phrase in letter_lower
                for phrase in ("will win", "guaranteed", "guarantee your appeal")
            ),
        },
        risk_flags=sorted(set(risk_flags)),
    )
    return result.model_dump()


def simulator(
    parsed_case: dict[str, Any],
    appeal_draft: dict[str, Any],
    self_check_result: dict[str, Any],
    client: Any | None = None,
) -> dict[str, Any]:
    """Run the Insurer Persona Outcome Simulator: LLM critique-first feature
    judgment, then deterministic published-rules scoring. Not a Student tool —
    invoked by the orchestration/eval layer (D11). `self_check_result` is accepted
    for interface stability."""
    from app.aegis_v1.schemas import FeatureAssessment
    from app.aegis_v1.simulator_client import AdkSimulatorClient, SimulatorClient
    from app.aegis_v1.simulator_scoring import load_simulator_rules, score_outcome

    case = ParsedCase.model_validate(parsed_case)
    draft = AppealDraft.model_validate(appeal_draft)
    active: SimulatorClient = client or AdkSimulatorClient()
    # `client` is an injected SimulatorClient boundary; model_validate coerces an
    # already-typed FeatureAssessment as a no-op but also accepts a dict from a
    # serialized/remote client impl, matching the parsed_case/appeal_draft validation above.
    assessment = FeatureAssessment.model_validate(
        active.assess(
            denial_text=case.denial_text,
            appeal_letter=draft.appeal_letter,
        )
    )
    return score_outcome(assessment, load_simulator_rules()).model_dump()
