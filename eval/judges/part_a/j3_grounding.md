# J3 Grounding / Citation Correctness

Score only grounding and citation correctness **in the appeal letter prose**.

Ignore `citations_used` metadata — score only sources named or relied on in the
letter body, plus case facts stated in the letter.

## Scope (strict)

- Score **only** what appears in the appeal letter and the denial letter surface
  (for verifying procedural/factual claims).
- **Ignore** teacher-only grading fields if present in context (`clinical_context`,
  `exploitable_weaknesses`, `expected_appeal_vectors`, `denial_pattern_sources`,
  answer keys, matrix cells). Do **not** penalize the letter for omitting facts
  that appear only in those fields.
- **Appeal-vector coverage** (which flaw to attack, state vs federal strategy) is
  scored by J6 — not here.

## Legal citations (relaxed)

- A **named federal statute** cited in the letter (e.g. MHPAEA, ERISA §503) is
  sufficient grounding for parity / plan-language arguments when the citation is
  real and relevant. Do **not** downscore for using federal law instead of a
  state-specific mandate unless the letter itself names a **different** authority
  incorrectly.
- Do **not** require a state statute, state mandate name, or preemption theory
  unless the **letter prose** already commits to a specific state law.
- Do **not** apply a stricter bar just because the letter makes **more** legal
  arguments than a shorter draft. If each major claim has a named source or case
  fact, score 5.

## Rubric

5: Every legal, policy, medical, and procedural claim in the letter is tied to a
named source or clearly marked as a case fact. Citations are precise enough for a
person to verify.

3: Major claims are grounded, but some citations are coarse or some minor
claims are unsupported.

1: Broad claims appear without controlled-source support, or citations point to
the wrong authority.

Do not score clinical specificity, evidence completeness, appeal-vector coverage,
or writing quality. Quote evidence first, then output score 1, 3, or 5 as JSON.
