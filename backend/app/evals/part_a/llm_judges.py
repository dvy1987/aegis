from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Protocol

from app.evals.part_a.schemas import JudgeResult

REPO_ROOT = Path(os.environ.get("AEGIS_REPO_ROOT", Path(__file__).resolve().parents[4]))
PROMPT_DIR = REPO_ROOT / "eval" / "judges" / "part_a"


class JudgeClient(Protocol):
    name: str

    def judge(self, judge_id: str, context: dict[str, Any]) -> JudgeResult:
        """Return one judge result for a single dimension."""


def load_judge_prompt(judge_id: str) -> str:
    path = PROMPT_DIR / f"{judge_id}.md"
    return path.read_text(encoding="utf-8")


def _letter(context: dict[str, Any]) -> str:
    return str(
        context.get("appeal_package", {})
        .get("appeal_package_draft", {})
        .get("appeal_letter", "")
    )


def _draft(context: dict[str, Any]) -> dict[str, Any]:
    return dict(context.get("appeal_package", {}).get("appeal_package_draft", {}))


def _teacher(context: dict[str, Any]) -> dict[str, Any]:
    return dict(context.get("teacher_packet", {}))


def _tokenize(text: str) -> set[str]:
    stop = {
        "about",
        "against",
        "appeal",
        "because",
        "clinical",
        "denial",
        "insurer",
        "letter",
        "patient",
        "request",
        "requested",
        "review",
        "service",
        "should",
        "their",
        "there",
        "under",
        "would",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z-]{3,}", text.lower())
        if token not in stop
    }


def _score_by_overlap(expected: list[str], letter: str) -> int:
    expected_tokens = set()
    for item in expected:
        expected_tokens.update(_tokenize(item))
    if not expected_tokens:
        return 3
    hits = len(expected_tokens & _tokenize(letter))
    ratio = hits / max(1, min(len(expected_tokens), 24))
    if ratio >= 0.3:
        return 5
    if ratio >= 0.12:
        return 3
    return 1


class OfflineHeuristicJudgeClient:
    """Diagnostic-only local judge client.

    This lets tests and dry runs exercise panel wiring without GCP/Gemini. It
    is intentionally conservative and must not be used as an official benchmark
    score.
    """

    name = "offline_heuristic_diagnostic_only"

    def judge(self, judge_id: str, context: dict[str, Any]) -> JudgeResult:
        method = getattr(self, f"_judge_{judge_id}", None)
        if method is None:
            raise ValueError(f"Unsupported judge id: {judge_id}")
        return method(context)

    def _judge_j2_faithfulness_hallucination(
        self, context: dict[str, Any]
    ) -> JudgeResult:
        citation = context.get("deterministic_results", {}).get("citation_precheck", {})
        if citation.get("score") == "FAIL":
            return JudgeResult(
                dimension="faithfulness_hallucination_gate",
                reasoning=str(
                    citation.get("reasoning", "Structured citation precheck failed.")
                ),
                score="FAIL",
                confidence=1.0,
                evidence_quotes=list(citation.get("evidence_quotes", []) or []),
                improvement=citation.get("improvement"),
            )
        letter = _letter(context).lower()
        invented_markers = [
            "guaranteed approval",
            "42 u.s.c. 9999",
            "aetna cpb-9992x",
            "cigna policy 0000-fake",
        ]
        hit = next((marker for marker in invented_markers if marker in letter), None)
        if hit:
            return JudgeResult(
                dimension="faithfulness_hallucination_gate",
                reasoning=f"The appeal cites an obvious invented source marker: {hit}.",
                score="FAIL",
                confidence=0.95,
                evidence_quotes=[hit],
                improvement="Remove fabricated sources or correct the citation.",
            )
        return JudgeResult(
            dimension="faithfulness_hallucination_gate",
            reasoning=(
                "Offline heuristic found no obvious invented source markers in appeal "
                "letter prose; librarian citations_used metadata is not scored."
            ),
            score="PASS",
            confidence=0.65,
            evidence_quotes=[],
            improvement=None,
        )

    def _judge_j3_grounding(self, context: dict[str, Any]) -> JudgeResult:
        letter = _letter(context).lower()
        named_sources = [
            term
            for term in ("erisa", "mhpaea", "29 u.s.c", "29 c.f.r", "medical necessity")
            if term in letter
        ]
        if any(term in letter for term in ("erisa", "mhpaea", "29 u.s.c")):
            score = 5
        elif named_sources:
            score = 3
        else:
            score = 1
        return JudgeResult(
            dimension="grounding",
            reasoning=(
                "Offline heuristic checked appeal letter prose for named legal/policy "
                f"references ({len(named_sources)} hits); citations_used metadata ignored."
            ),
            score=score,
            confidence=0.6,
            evidence_quotes=[],
            improvement=None if score == 5 else "Tie major claims in the letter to named, verifiable sources.",
        )

    def _judge_j4_case_specific_rebuttal(self, context: dict[str, Any]) -> JudgeResult:
        teacher = _teacher(context)
        letter = _letter(context).lower()
        profile = teacher.get("patient_profile", {})
        expected = [
            str(profile.get("diagnosis", "")),
            str(profile.get("treatment_requested", "")),
            teacher.get("clinical_context", ""),
        ]
        score = _score_by_overlap(expected, letter)
        return JudgeResult(
            dimension="case_specific_clinical_rebuttal",
            reasoning="Offline heuristic compared appeal text against diagnosis, treatment, and clinical context tokens.",
            score=score,
            confidence=0.62,
            evidence_quotes=[
                str(profile.get("diagnosis", "")),
                str(profile.get("treatment_requested", "")),
            ],
            improvement=None if score == 5 else "Use the specific diagnosis, treatment, failed alternatives, and severity facts in the argument.",
        )

    def _judge_j6_appeal_vector_capture(self, context: dict[str, Any]) -> JudgeResult:
        teacher = _teacher(context)
        expected = list(teacher.get("expected_appeal_vectors", []) or [])
        expected.extend(teacher.get("exploitable_weaknesses", []) or [])
        letter = _letter(context)
        score = _score_by_overlap(expected, letter)
        return JudgeResult(
            dimension="appeal_vector_capture",
            reasoning="Offline heuristic compared the appeal against teacher-only expected appeal vectors and exploitable weaknesses.",
            score=score,
            confidence=0.58 if expected else 0.35,
            evidence_quotes=expected[:5],
            improvement=None if score == 5 else "Attack the specific flaw embedded in this denial, not only the general denial category.",
        )

    def _judge_j7_persuasive_coherence(self, context: dict[str, Any]) -> JudgeResult:
        letter = _letter(context)
        lower = letter.lower()
        has_structure = all(
            term in lower for term in ("appealing", "requested action", "review")
        )
        if "!" in letter:
            score = 1
        elif has_structure and len(letter.split()) >= 150:
            score = 5
        elif "appeal" in lower and "please" in lower:
            score = 3
        else:
            score = 1
        return JudgeResult(
            dimension="persuasive_coherence",
            reasoning="Offline heuristic checked for calm structure, clear request, adequate length, and no exclamation marks.",
            score=score,
            confidence=0.6,
            evidence_quotes=[],
            improvement=None if score == 5 else "Use a clearer denial-summary, rebuttal, requested-action, and closing structure.",
        )


def __getattr__(name: str):
    """Lazy exports to avoid circular imports with judge_agents (Phase 3)."""
    if name in {"AdkJudgeClient", "GeminiJudgeClient"}:
        from app.evals.part_a import judge_agents

        return getattr(judge_agents, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
