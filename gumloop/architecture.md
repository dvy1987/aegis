# Gumloop Swarm: Synthetic Case Realism Evaluation

This folder contains the architecture and prompts for the Gumloop multi-agent flow designed to evaluate the realism of synthetic denial cases.

## Core Principle — "Flaws Are Features"

**The denial letters in these cases are intentionally imperfect.** The P4 Realistic Flaw Injector has deliberately embedded documented real-world insurer patterns into each denial letter — circular reasoning, missing ERISA disclosures, algorithmic boilerplate, ignored physician evidence, vague guideline citations, and more.

**All 17 critic prompts are written with this in mind.** Critics must NOT penalise a denial letter for being vague, cold, legally incomplete, or logically weak. These properties signal a well-generated case. Critics penalise only:
- Medically impossible patient scenarios
- Internal contradictions in core facts
- Out-of-scope insurance types
- PHI / safety violations
- AI-writing-style tells (not the same as intentional insurer flaws)
- Hallucinated guideline names that couldn't plausibly be real

---

## Orchestration Pattern

**Parallel** (17 specialist critics fan-out, 1 Arbiter fans-in). Critics run in parallel to minimise latency and prevent anchoring bias. The Arbiter applies tiered logic.

---

## Wiring Diagram (Gumloop Flow)

```mermaid
graph TD
    A[Input Node: Case JSON + denial_pattern_sources] --> B(Fan-out to Evaluators)
    
    subgraph Tier 1: Hard Gates — DISCARD if FAIL
    B --> C1[Contradiction Hunter]
    B --> C2[Scope Guard]
    B --> C3[Safety Redactor]
    B --> C4[Diagnosis-Treatment Match]
    B --> C5[Demographic Validator]
    end
    
    subgraph Tier 2: Realism Critics — REVISE if score = 1 or FAIL
    B --> D0[18 Flaw Injection Verifier ★ HIGHEST PRIORITY]
    B --> D1[Clinical Critic]
    B --> D2[Tone Critic]
    B --> D3[LLM Tell Detector]
    B --> D4[Financial Auditor]
    B --> D5[Legal Auditor]
    B --> D6[Insurer Voice]
    B --> D7[Denial Logic]
    B --> D8[Date Sanity]
    B --> D9[Citation Traceability]
    end

    subgraph Internal Meta-Evaluators — Informational only, never gate
    B --> E1[Realism Assessor]
    B --> E2[Appeal Difficulty]
    end
    
    C1 & C2 & C3 & C4 & C5 --> J(Fan-in)
    D0 & D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 & D9 --> J
    E1 & E2 --> J
    
    J --> K[LLM Node: Final Arbiter]
    K --> L{Verdict Router Node}
    L -- DISCARD --> M[Output: Delete Draft]
    L -- REVISE --> N[Output: Send back to Drafter with specific actionable instructions]
    L -- APPROVE --> O[Output: Move to Approved Folder and write Provenance]
```

---

## Tiered Arbiter Logic

| Tier | Critics | Trigger Condition | Result |
|---|---|---|---|
| **Tier 1 Hard Gates** | Contradiction Hunter, Scope Guard, Safety Redactor, Dx-Tx Match, Demographic Validator | Any FAIL | DISCARD (no exceptions) |
| **Tier 2 Realism Critics** | **Flaw Injection Verifier** ★, Clinical, Tone, LLM Tell, Financial, Legal, Insurer Voice, Denial Logic, Date Sanity, Citation | Score = 1 OR FAIL | REVISE |
| **Meta-Evaluators** | Realism Assessor, Appeal Difficulty | Any score | Informational only — never gate |

★ **Flaw Injection Verifier is the highest-priority Tier 2 critic.** If it scores 1 (an intended flaw is missing from the denial letter), the case is always REVISE regardless of other critics passing. The case cannot be benchmark-useful until all intended flaws are actually present.

**PREFER APPROVE:** If all Tier 1 gates PASS and no Tier 2 critic scores 1, the case APPROVES. A score of 3 from any Tier 2 critic is acceptable.

**Appeal Difficulty** is explicitly hidden from Phoenix traces and must not be referenced in REVISE instructions or APPROVE reasons. It feeds the teacher packet only.

---

## Flaw Patterns and Their Correct Handling

The following patterns are injected by P4 and must NOT trigger REVISE/DISCARD:

| Pattern ID | What it injects | Which critics must NOT penalise |
|---|---|---|
| `step_therapy_vague_mcg` | Vague MCG citation, no edition | Legal Auditor, Citation Traceability |
| `missing_erisa_disclosures` | Missing ERISA § 1133 rights | Legal Auditor |
| `missing_iro_notice` | No external review notice | Legal Auditor |
| `missing_cost_liability` | No financial liability statement | Financial Auditor |
| `circular_medical_necessity` | "Not necessary because doesn't meet necessity criteria" | Denial Logic (this is a SCORE 5 for denial_logic) |
| `ignored_physician_letter` | Denial ignores all submitted evidence | Clinical Critic, Contradiction Hunter |
| `algo_boilerplate_fingerprint` | Zero case-specific language | Insurer Voice, LLM Tell Detector (this is NOT an LLM tell) |
| `algo_time_delta` | 1–5 min between submission and denial | Date Sanity (must NOT flag this as a date error) |
| `superseded_guideline` | Cites outdated InterQual/MCG | Legal Auditor, Citation Traceability |
| `non_specialist_reviewer` | Reviewer credentials absent | Legal Auditor |

---

## Setup Instructions for Gumloop

1. Create an **Input Node** that accepts the raw `JSON` of a synthetic case (full `CaseDraft` schema including `synthetic_provenance`).
2. Create **16 Parallel LLM Nodes** — one for each critic prompt file.
3. Paste the prompt from the `/prompts` folder into each respective LLM Node.
4. Set each LLM node to return structured JSON as defined in each prompt's OUTPUT section. Set temperature to 0.3 for critics (low variance).
5. Fan all 16 outputs into the **Final Arbiter** LLM Node (prompt `08_final_arbiter.txt`).
6. Wire the Arbiter's `verdict` field to a **Router Node**: `DISCARD` → delete, `REVISE` → return to generator with `suggested_revisions`, `APPROVE` → write to `eval/cases/approved/`.
7. When writing approved cases, save the `Appeal Difficulty` score and `exploitable_weaknesses` from prompt `10_appeal_difficulty.txt` into the `synthetic_provenance.appeal_difficulty` field — this feeds the teacher packet for the judge panel.
