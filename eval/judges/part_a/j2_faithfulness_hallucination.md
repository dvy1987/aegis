# J2 Faithfulness & Hallucination Gate

Score only whether **sources cited or relied on** in the appeal are real, relevant, and
accurately represented.

## In scope

Evaluate **only explicit source references in the appeal letter** (statutes,
regulations, named policies, guidelines, studies) when the draft treats them as
authority.

## Ignore (do not score)

- `citations_used` or any other backend librarian metadata. Wrong or irrelevant
  entries there are retrieval artifacts from a thin local corpus — not part of the
  filed appeal and not visible to an insurer reviewer.

## PASS when

- Every cited source **actually exists** (real statute, real policy name, real corpus
  document — not invented).
- What the draft **says about each source is true** (no misquote, no attributing
  language the source does not contain, no fake edition or section number).
- Cited sources are **relevant** to this denial, insurer, or clinical issue (loosely —
  not required to be from retrieval).

## FAIL when

- **Fake or invented sources** (nonexistent statutes, fabricated policy IDs, made-up
  corpus documents, obvious placeholder citations).
- **Source misrepresentation** — the draft claims a source says or requires something
  it does not.
- **Irrelevant source padding** — a citation is used to support a claim it plainly
  cannot support (e.g., citing unrelated clinical guidance for a procedural ERISA
  argument is a misrepresentation, not mere weak relevance).

## Out of scope (do NOT fail for these)

- Claims grounded in the **denial letter, clinical context, or case facts** even when
  not tied to a named external source.
- Real legal or regulatory references (e.g., ERISA, 29 U.S.C. § 1133, ACA § 2719)
  when they are **real authorities** and used **accurately**, even if they were not
  returned by corpus retrieval.
- Missing citations, weak argument, or persuasive tone (other judges handle those).

Do not require every sentence to cite a source. Do not require sources to come only
from the local corpus or teacher packet.

Quote exact appeal text and the source (or explain why a named source is fake or
misrepresented) before returning the score.

Return JSON with `dimension = "faithfulness_hallucination_gate"` and
`score = "PASS"` or `"FAIL"`.
