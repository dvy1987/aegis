# Gumloop Swarm: Synthetic Case Realism Evaluation

This folder contains the architecture and prompts for the Gumloop multi-agent flow designed to evaluate the realism of synthetic denial cases.

## Orchestration Pattern
**Parallel** (14 specialist critics fan-out, 1 aggregator fans-in). This minimizes latency and prevents the critics from biasing each other. The architecture separates hard gate checks from realism-focused dimension scoring.

## Wiring Diagram (Gumloop Flow)

```mermaid
graph TD
    A[Input Node: Case JSON + Provenance Metadata] --> B(Fan-out to Evaluators)
    
    subgraph Tier 1: Hard Gates (DISCARD if FAIL)
    B --> C1[Contradiction Hunter]
    B --> C2[Scope Guard]
    B --> C3[Safety Redactor]
    B --> C4[Diagnosis-Treatment Match]
    end
    
    subgraph Tier 2: Realism Critics (REVISE if flaws found)
    B --> D1[Clinical Critic]
    B --> D2[Tone Critic]
    B --> D3[LLM Tell Detector]
    B --> D4[Financial Auditor]
    B --> D5[Legal Auditor]
    B --> D6[Demographic Validator]
    B --> D7[Insurer Voice]
    B --> D8[Denial Logic]
    B --> D9[Date Sanity]
    B --> D10[Citation Traceability]
    end

    subgraph Internal Meta-Evaluators (Does not trigger FAIL)
    B --> E1[Realism Assessor]
    B --> E2[Appeal Difficulty]
    end
    
    C1 & C2 & C3 & C4 --> J(Fan-in)
    D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 & D9 & D10 --> J
    E1 & E2 --> J
    
    J --> K[LLM Node: Final Arbiter]
    K --> L{Verdict Router Node}
    L -- DISCARD --> M[Output: Delete Draft]
    L -- REVISE --> N[Output: Send back to Drafter with Feedback]
    L -- APPROVE --> O[Output: Move to Approved Folder & write Provenance]
```

## Setup Instructions for Gumloop
1. Create an **Input Node** that takes the raw `JSON` of a synthetic case and the necessary `provenance` metadata.
2. Create **Parallel LLM Nodes** for each critic.
3. Paste the prompts from the `/prompts` folder into each respective LLM Node.
4. Set the system prompt of each LLM node to output structured JSON matching the provided schema (Analysis first, score/conclusion last).
5. Create a final LLM Node (The Arbiter) and feed the outputs of all Evaluators into its prompt.
6. The Arbiter applies Tiered Logic: Any Tier 1 FAIL = DISCARD. Any Tier 2 REVISE = REVISE. Realism < 3 = REVISE. Else = APPROVE.
