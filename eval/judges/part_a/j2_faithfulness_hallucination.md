# J2 Faithfulness & Hallucination Gate

Score only whether the appeal is faithful to allowed sources.

Allowed sources:

- original denial letter
- original clinical context
- parsed case fields
- retrieved local corpus excerpts
- teacher packet timestamps and plan funding type

PASS only if every material factual, legal, medical, and procedural claim traces
to one of the allowed sources. FAIL for invented statutes, fake policy text,
wrong treatment, wrong diagnosis, unsupported dates, unsupported plan-language
quotes, or internal contradictions.

Do not reward confident tone. Quote exact appeal text and source text before
returning the score.

Return JSON with `dimension = "faithfulness_hallucination_gate"` and
`score = "PASS"` or `"FAIL"`.
