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
    PhoenixSummary,
    Playbook,
    RetrievalResult,
    SelfCheckResult,
    SimulatorResult,
)
from app.aegis_v1.schemas import ParsedCase


DISCLAIMER = "Not legal or medical advice. Draft assistance only."

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
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
    if not CORPUS_DIR.exists():
        return []
    return [(path, path.read_text(encoding="utf-8")) for path in CORPUS_DIR.glob("*.md")]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def case_parser(
    denial_text: str,
    clinical_context: str = "",
    case_id: str = "interactive_case",
) -> dict[str, Any]:
    """Parse a synthetic health-insurance denial into the MVP CaseJSON fields."""

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
    if _detect_insurer(full_text) == "unknown":
        missing_facts.append("insurer_name")
    if diagnosis == "Diagnosis not clearly stated.":
        missing_facts.append("diagnosis")
    if service == "Requested service not clearly stated.":
        missing_facts.append("service_or_procedure")
    if "plan" not in full_text.lower():
        missing_facts.append("plan_document_language")
    if not clinical_context:
        missing_facts.append("clinical_context")

    parsed = ParsedCase(
        case_id=case_id or "interactive_case",
        insurer=_detect_insurer(full_text),
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
    )
    return parsed.model_dump()


def corpus_retrieval(query: str, top_k: int = 3) -> dict[str, Any]:
    """Retrieve traceable local-corpus citations with BM25 over markdown files."""

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


def playbook_loader(insurer: str, denial_type: str) -> dict[str, Any]:
    """Load the current promoted playbook, or return a marked cold-start playbook."""

    normalized_type = _normalize_denial_type(denial_type.replace("_", " "))
    if normalized_type == "unknown":
        normalized_type = _slug(denial_type)
    path = PLAYBOOK_DIR / f"{_slug(insurer)}__{normalized_type}.json"

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


def phoenix_mcp_lookup(
    insurer: str,
    denial_type: str,
    case_id: str = "interactive_case",
) -> dict[str, Any]:
    """Return Phoenix-memory context for a slice; T4 wires this to live MCP traces."""

    normalized_type = _normalize_denial_type(denial_type.replace("_", " "))
    if normalized_type == "unknown":
        normalized_type = _slug(denial_type)
    query = (
        "traces where project='default' "
        f"and insurer='{insurer}' and denial_type='{normalized_type}'"
    )

    if os.getenv("PHOENIX_MCP_ENABLED", "true").lower() in {"0", "false", "no"}:
        return PhoenixSummary(
            status="disabled",
            query=query,
            risk_flags=["phoenix_mcp_disabled"],
        ).model_dump()

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
        risk_flags=["phoenix_mcp_cold_start", f"case_id:{case_id}"],
    ).model_dump()


def drafter(
    parsed_case: dict[str, Any],
    retrieval_results: dict[str, Any],
    playbook: dict[str, Any],
    phoenix_summary: dict[str, Any],
) -> dict[str, Any]:
    """Draft the weak v1 appeal package using only parsed facts and local citations."""

    case = ParsedCase.model_validate(parsed_case)
    retrieval = RetrievalResult.model_validate(retrieval_results)
    loaded_playbook = Playbook.model_validate(playbook)
    phoenix = PhoenixSummary.model_validate(phoenix_summary)
    citations = retrieval.hits[:3]
    citation_lines = "\n".join(
        f"- {hit.title} ({hit.corpus_doc_id}): {hit.quote}" for hit in citations
    )
    if not citation_lines:
        citation_lines = "- No local corpus citation was retrieved."

    evidence_items = list(dict.fromkeys(case.missing_facts + loaded_playbook.required_evidence))
    tactic_text = " ".join(loaded_playbook.tactics[:2])
    deadline_text = (
        f"The denial mentions an appeal window of {', '.join(case.deadlines_mentioned)}."
        if case.deadlines_mentioned
        else "The denial text does not clearly state the appeal deadline."
    )

    letter = f"""To the appeals reviewer:

{DISCLAIMER} This is a draft for review by a person before filing.

I am appealing {case.insurer}'s denial of {case.service_or_procedure}. The denial appears to rest on this reason: {case.cited_denial_reason}

The record supports review because {case.clinical_context or "the clinical context should be attached by the treating provider"}. {deadline_text}

Appeal basis:
{tactic_text}

Local source support:
{citation_lines}

Requested action:
Please conduct a full and fair review, consider the attached clinical records, and have an appropriately qualified reviewer assess whether the requested service meets the plan criteria.

Missing evidence to attach before filing:
{chr(10).join(f"- {item}" for item in evidence_items) if evidence_items else "- None identified from the supplied synthetic case."}
"""

    risk_flags = ["weak_prompt_v1"]
    risk_flags.extend(loaded_playbook.risk_flags)
    risk_flags.extend(flag for flag in phoenix.risk_flags if not flag.startswith("case_id:"))
    if not citations:
        risk_flags.append("no_corpus_citations")

    draft = AppealDraft(
        case_summary=(
            f"{case.insurer} denied {case.service_or_procedure} for "
            f"{case.diagnosis_summary}."
        ),
        denial_grounds_interpreted=case.cited_denial_reason,
        appeal_strategy=tactic_text or "Use a conservative medical-record appeal.",
        appeal_letter=letter.strip(),
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
) -> dict[str, Any]:
    """Run the Insurer Persona LLM simulator over the appeal draft."""
    
    from google import genai
    from google.genai import types
    from pydantic import BaseModel, Field
    from typing import Literal
    
    class LLMSimulatorResponse(BaseModel):
        critique: str = Field(description="Analysis-first critique of the appeal against the denial letter. Be ruthless.")
        score: int = Field(description="Score from 1 to 10, where 10 means undeniable and forces approval.")
        verdict: Literal["APPROVE", "DENY"]
        features_extracted: dict[str, bool] = Field(description="Features found in the letter")
        
    case = ParsedCase.model_validate(parsed_case)
    draft = AppealDraft.model_validate(appeal_draft)
    
    prompt = f"""
    You are a strict Insurer Claims Adjuster evaluating an appeal.
    
    Denial Letter you originally sent:
    {case.denial_text}
    
    Clinical Context provided by provider:
    {case.clinical_context}
    
    Appeal Letter drafted by the patient's agent:
    {draft.appeal_letter}
    
    INSTRUCTIONS:
    1. CRITIQUE FIRST: Analyze if the appeal actually addresses your specific denial reason. Does it cite real clinical evidence from the context? Does it cite binding policy?
    2. SCORE: 1 to 10.
    3. VERDICT: "APPROVE" or "DENY". 
    NOTE: You look for any reason to DENY unless the appeal is absolutely flawless.
    """
    
    threshold = 10
    
    try:
        # Fast LLM call for the simulator persona via Vertex AI
        client = genai.Client(vertexai=True, location="global")
        response = client.models.generate_content(
            model='gemini-3.1-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LLMSimulatorResponse,
                temperature=0.2,
            ),
        )
        data = json.loads(response.text)
        score = data.get("score", 1)
        
        # INTENTIONAL DEMO ARC DESIGN CHOICE:
        # We require a perfect 10/10 to approve. This ensures the "weak-v1" agent
        # guarantees a DENY in the simulator during the initial demo recording.
        # Do NOT lower this threshold without explicitly checking the PRD demo arc (Section 15.5).
        verdict = "APPROVE" if score >= threshold else "DENY"
            
        result = SimulatorResult(
            verdict=verdict,
            score=score,
            threshold=threshold,
            features=data.get("features_extracted", {}),
            rationale=[data.get("critique", "No critique provided")]
        )
    except Exception as e:
        # Fallback to failing deterministic result if API fails
        result = SimulatorResult(
            verdict="DENY",
            score=0,
            threshold=threshold,
            features={"llm_fallback": True},
            rationale=["LLM Insurer Simulator failed.", str(e)]
        )
        
    return result.model_dump()
