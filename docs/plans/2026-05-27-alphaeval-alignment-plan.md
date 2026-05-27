# Goal: Align Case Evaluation with AlphaEval 2026 Principles

You are entirely correct. While the Gumloop swarm is for evaluating *synthetic cases* (not the final appeal letters), the underlying architectural principles from **AlphaEval 2026** (which we rigorously defined in `docs/evals/2026-05-27-aegis-appeal-rubric.md`) absolutely apply here. 

I drifted into AI-defaults and violated several core AlphaEval principles. Here is the audit of where we failed, and the plan to fix it.

## The Violations

1. **Scale Drift (Violates AlphaEval 1/3/5 forced anchor scoring):**
   - **Current:** My prompts ask for `[Score 1-5]` and the Arbiter logic relies on "mostly 2s and 3s". 
   - **AlphaEval rule:** "No 2s or 4s — forced anchor scoring 1/3/5 per AlphaEval (reduces judge drift toward the middle)."

2. **Hard Gates vs Weighted Averages (Violates AlphaEval gating rules):**
   - **Current:** The Arbiter looks at all 7 scores and averages them out ("predominantly 4s and 5s"). 
   - **AlphaEval rule:** Safety and Hallucination must be binary PASS/FAIL hard gates that short-circuit the evaluation. They should never be scored on a continuum and averaged with tone.

3. **Mega-Prompt Contamination (Violates AlphaEval independent judge rule):**
   - **Current:** The manual ChatGPT and Perplexity prompts I just wrote are massive 8-metric mega-prompts.
   - **AlphaEval rule:** "❌ One mega-prompt judge covering all 7 concerns (cross-dimension contamination)."

*(Note: The Gumloop structure itself—7 parallel independent judges doing Chain of Thought first—is perfectly compliant. It's the scales, gates, and manual mega-prompts that are broken).*

## Proposed Changes

### 1. Fix Gumloop Prompt Scales
- **[MODIFY]** `gumloop/prompts/01` through `gumloop/prompts/07`: Change the scoring instruction from `[Score 1-5]` to a strict `[Score 1, 3, or 5]` forced scale.

### 2. Implement Binary Hard Gates
- **[MODIFY]** `03_llm_tell_detector.txt` and `06_contradiction_hunter.txt`: Convert these two from a 1/3/5 scale into strict binary `[PASS or FAIL]` gates. An LLM tell or a contradiction is a fatal flaw for a realistic case, not a dimension to be averaged.
- **[MODIFY]** `08_final_arbiter.txt`: Update the Arbiter logic. 
  - If Tell Detector or Contradiction Hunter == FAIL → Verdict is `DISCARD`.
  - If remaining judges score 1s → Verdict is `DISCARD`.
  - If remaining judges score mostly 3s → Verdict is `REVISE`.
  - If remaining judges score predominantly 5s → Verdict is `APPROVE`.

### 3. Address the Mega-Prompt Anti-Pattern
I need your direction on the `chatgpt` and `perplexity` manual prompts. AlphaEval strictly forbids mega-prompts because the LLM gets confused and bleeds dimensions together. 

**Options:**
- **Option A (Kill them):** Delete the ChatGPT/Perplexity mega-prompts entirely and strictly enforce that *all* case evaluation must run through the 8-node Gumloop swarm.
- **Option B (Dirty Spot-Check):** Keep them, but add a huge warning at the top of the prompts that they violate AlphaEval and are strictly for "dirty/fast human vibe checks," not for the official benchmark promotion.

## Open Questions

**Decision Needed:** How would you like to handle the ChatGPT and Perplexity mega-prompts (Option A or Option B)? 

Once you approve, I will immediately execute the fixes across the Gumloop folder.
