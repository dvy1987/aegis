# LLM Judges Specification: Aegis

## Judge Overview
Aegis relies on a 7-judge panel in Phoenix to score appeal letters against the AlphaEval 2026 rubric. 
To mitigate self-enhancement bias, the judge model must be different from the drafting model (e.g., if Gemini 3 drafts, use Claude 4 or GPT-5 as the primary judge if available, or a differently-tuned Gemini variant).

## Judge Modes

### 1. Direct Scoring (Primary CI Gate)
Used to score individual drafted appeal letters against the rubric.

**Judge Prompt Structure (Bias Mitigation + CoT):**
```
You are an expert evaluator of health insurance appeal letters.
You must evaluate the provided appeal letter against the provided rubric.

CRITICAL INSTRUCTIONS:
1. Do NOT prefer responses because they are longer. A concise, accurate letter is better than a long, rambling one.
2. Do NOT be swayed by an authoritative tone if the facts are missing.
3. You MUST provide your chain-of-thought reasoning before outputting the score.
4. For Hard Gates, output PASS or FAIL. If any gate fails, the overall verdict is FAIL.

For each dimension in the rubric, format your response as:
Evidence: [quote specific text from the letter]
Reasoning: [explain how the evidence maps to the score descriptions]
Score: [1, 3, or 5]
Improvement: [one specific, actionable fix]
```

### 2. Pairwise Comparison (A/B Testing & Promotion Gate)
Used when a specialist agent proposes a new prompt or playbook, and we must prove it outperforms the baseline before merging.

**Judge Prompt Structure (Position Bias Mitigation):**
```
You are an expert evaluator. Compare Response A and Response B.

CRITICAL INSTRUCTIONS:
1. Do NOT prefer responses because they are longer.
2. Do NOT prefer responses based on their position (Response A vs Response B).
3. Focus ONLY on the quality according to the rubric criteria.
4. Ties are acceptable when responses are genuinely equivalent.

Provide reasoning based on the rubric, then state your final verdict: [A / B / TIE].
```
*Note: The evaluation pipeline must run this twice per comparison, swapping positions (A first, then B first). If passes disagree, output is TIE with 0.5 confidence.*

## Internal Consistency Check (Long-form verification)
Before final quality scoring, the judge must verify internal consistency:
1. Numeric consistency: Are dates, denial codes, and bill amounts identical across sections?
2. Factual consistency: Do assertions in paragraph 1 contradict claims in paragraph 4?
3. Logical consistency: Does the demand match the cited denial reason?

Any contradiction triggers an immediate FAIL on the Hard Gate.

## Confidence Scoring
Judges must output a confidence score (0.0 - 1.0) for each dimension:
- **0.9-1.0:** Clear evidence, unambiguous score.
- **0.6-0.8:** Evidence present but some interpretation needed.
- **0.3-0.5:** Ambiguous or edge case.
- **<0.3:** Cannot reliably score — flagged for human PM review.
