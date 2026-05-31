# Reflection — Round 1 — target dimension: `appeal_vector_capture`

**Reflector:** the Claude Code session (no API key; the session itself is the intelligence).
**Parent component:** `drafter_v1.md` → **child:** `drafter_v2.md`.
**Targeted because:** it is the weakest *promptable* dimension on the train slice
(train mean anchor 3.5; case_01=5, case_03/05/02=3). `grounding` is tied-lowest (3.0) but is
corpus-bound — no prompt change can move it without retrieved citations — so it is excluded as a
target (documented, honest).

## Critique (diagnosis before edit)
Across the train drafts the v1 letters surface the right clinical facts but present them as merely
"relevant" and ask the insurer to "reconsider/clarify." Two systematic gaps drop the score to 3:
1. They do not **confront the insurer's strongest stated ground** — they argue *around* the named
   criterion/threshold instead of applying it to the documented facts (or arguing for an exception
   when the patient does not literally meet it).
2. They never **audit the denial for missing procedural / appeal-rights disclosures**, which several
   denials omit — a standing, case-independent opening.

## Edit (small, attributable, one dimension)
Added a single "Capture this denial's specific appeal vector" section with exactly the two levers
above and an instruction to make the specific-flaw argument the spine of the letter. **+131 words
(~170 tokens)** over v1 — under the 200-token focused-diff cap. No other section changed.

## Constraints honored
- Canonical disclaimer / citation-only / no-exclamation / no-win-claim rules kept verbatim.
- Did **not** target the insurer APPROVE/DENY verdict (INV-3) — targets the judge quality dimension.
- Inputs to this reflection were the **laundered** train improvement notes only (denial/clinical
  facts), never the teacher answer-key fields — INV-2 firewall held on the reflection input.

## Laundered train notes that drove the edit (verbatim, firewall-clean)
- case_03: "…you present them as merely 'relevant'… affirmatively argue that the named guideline,
  applied to these documented findings, points toward the requested level of care… scan the denial
  letter for what it failed to include about the member's process options."
- case_05: "…you never engage the denial's literal rule… Name that gap head-on and argue why a fixed
  coverage threshold should yield to an individualized medical-necessity exception…"
- case_02: "…read [the denial] for what it fails to provide… discloses no appeal rights, deadline, or
  process… Auditing the denial for missing procedural disclosures should be a standard pass."
