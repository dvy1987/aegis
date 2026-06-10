# J3 Grounding / Citation Correctness

Score only grounding and citation correctness **in the appeal letter prose**.

Ignore `citations_used` metadata — score only sources named or relied on in the
letter body, plus case facts stated in the letter.

5: Every legal, policy, medical, and procedural claim in the letter is tied to a
named source or clearly marked as a case fact. Citations are precise enough for a
person to verify.

3: Major claims are grounded, but some citations are coarse or some minor
claims are unsupported.

1: Broad claims appear without controlled-source support, or citations point to
the wrong authority.

Do not score clinical specificity, evidence completeness, or writing quality.
Quote evidence first, then output score 1, 3, or 5 as JSON.
