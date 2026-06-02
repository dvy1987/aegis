from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypedDict


Verdict = Literal["APPROVE", "REVISE", "DISCARD"]
PassFail = Literal["PASS", "FAIL"]


class CriticOutputBase(TypedDict, total=False):
    dimension: str
    analysis: str
    confidence: float
    evidence_quotes: list[str]
    improvement: str | None


class PassFailCriticOutput(CriticOutputBase):
    verdict: PassFail


class ScoreCriticOutput(CriticOutputBase):
    score: int


class FlawInjectionResult(TypedDict):
    pattern_id: str
    status: Literal["PRESENT", "ABSENT", "AMBIGUOUS"]
    evidence: str


class FlawInjectionVerifierOutput(CriticOutputBase):
    dimension: Literal["flaw_injection_verification"]
    denial_pattern_sources_found: list[str]
    verification_results: list[FlawInjectionResult]
    score: Literal[1, 3, 5]
    score_meaning: dict[str, str]
    confidence: float
    improvement: str | None


class ArbiterOutput(TypedDict):
    case_id: str
    evaluator: Literal["Gumloop"]
    verdict: Verdict
    reason: str
    tier_1_failures: list[str]
    tier_2_failures: list[str]
    suggested_revisions: list[str]


@dataclass(frozen=True)
class GumloopRunResult:
    case_id: str
    arbiter: ArbiterOutput
    critic_outputs: dict[str, dict[str, Any]]

