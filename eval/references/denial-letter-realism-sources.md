# Denial letter realism references

Public sources used to calibrate **surface realism** of synthetic commercial denial letters in `eval/cases/drafts/`. This does **not** change case construction, injected flaws, or matrix cells.

Machine-readable catalog: [`denial-letter-realism-sources.json`](denial-letter-realism-sources.json).

## What real letters do that ours lacked

| Real pattern | Source | Our prior gap |
|---|---|---|
| Labeled **adverse benefit determination** / formal notice title | CMS model ABD; ERISA | Generic "Dear Member" only |
| **Case-details block** (member ID, auth/claim ref, DOS, provider) | CMS model ABD; 29 CFR § 2590.715-2719 | No identifiers |
| **Denial / remark code** with plain meaning (e.g. CO-96) | HIPAA 835 / plan materials | No codes |
| **Named policy instrument** (CPB #, CDG #, coverage policy #) | Insurer public policies; appeal guides | Generic "MCG/InterQual" only |
| **Plan provision** pointer (SPD / EOC section) | 29 CFR § 2560.503-1 | Absent |
| Codes available **on request** | ACA § 2719 | Not mentioned |
| **Internal + external (IRO)** appeal rights | CMS/CCIIO; state OIC | Often vague; flaws may omit IRO |
| Peer-to-peer / physician review line | Industry practice | One generic sentence |

## What we deliberately did not copy

- Verbatim text from insurer PDFs or member-specific notices
- Medicare Integrated Denial Notice (CMS-10003) layout — out of MVP scope
- Real member names, addresses, or claim numbers

## Per-case storage

Each rebuilt case may include `denial_letter_references`: an array of `{ ref_id, title, url, source_type, relevance }` pointing at entries in the JSON catalog plus pattern-specific regulatory citations from `denial_pattern_sources`.

## Generator

`backend/app/case_generator/aplus/letters.py` (P2) — version `1.1.0` as of 2026-06-02 realism pass.
