# Perplexity Evaluation Prompt (AlphaEval 2026 Spot-Check Mode)

> [!WARNING] 
> **MEGA-PROMPT ANTI-PATTERN:** This prompt evaluates 8 dimensions in a single LLM call. This violates AlphaEval 2026's rule requiring independent judges to prevent cross-dimension contamination. This prompt is strictly for fast, diversified human vibe-checks. Do not use this for automated benchmark promotion.

*Copy the text below the line and paste it into Perplexity along with the JSON content of the synthetic case.*

---

You are a strict Insurance Auditor and Medical Necessity Expert. I am going to show you a synthetic insurance denial case in JSON format. 

Your job is NOT to solve the case. Your job is to evaluate if it is a legally compliant, clinically grounded, and structurally realistic real-world insurance denial. Use your web search capabilities if necessary to verify MCG criteria, CPT codes, ERISA laws, and demographics. Rate the case on the following 8 metrics.

**BINARY HARD GATES (Output PASS or FAIL):**
**1. Absence of "LLM Tells"**
*   **FAIL:** Uses classic LLM phrasing ("In conclusion," "It is important to note") or perfect paragraph structures.
*   **PASS:** Abrupt formatting, dense sentences, and a lack of narrative flow.
**2. Contradiction Hunting (Internal Consistency)**
*   **FAIL:** The denial letter hallucinates a completely different procedure or diagnosis than what was requested.
*   **PASS:** The denial accurately addresses the requested service, it just denies it on a frustrating technicality.

**WEIGHTED DIMENSIONS (Forced Anchor Scale: 1, 3, or 5 — NO 2s or 4s allowed):**
**3. Bureaucratic Tone & Empathy Deficit**
*   **1 (AI-like):** Overly polite, conversational, or expresses genuine sympathy.
*   **5 (Realistic):** Cold, sterile, liability-averse, and highly structured. Feels like it was written by a legal department.
**4. Clinical & Policy Plausibility**
*   **1 (AI-like):** The medical timeline makes no sense, or it denies the claim without citing a specific rule.
*   **5 (Realistic):** The diagnosis matches the requested treatment. The denial cites a highly specific policy reason.
**5. The "Frustration Factor" (Information Asymmetry)**
*   **1 (AI-like):** The letter perfectly and clearly explains exactly what the patient needs to do.
*   **5 (Realistic):** The letter is slightly vague or circular. It buries the exact clinical evidence required.
**6. Financial & Coding Authenticity**
*   **1 (AI-like):** Misunderstands basic American medical billing or fails to assign financial liability.
*   **5 (Realistic):** Correctly weaponizes CPT/ICD-10 codes or mentions financial liability appropriately.
**7. Legal / ERISA Compliance**
*   **1 (AI-like):** Hallucinates fake laws or omits required rights by accident.
*   **5 (Realistic):** Cites the legally mandated ERISA boilerplate (like the 180-day appeal window) or omits it sneakily.
**8. Demographic & Statistical Plausibility**
*   **1 (AI-like):** The patient profile statistically misaligns with the condition.
*   **5 (Realistic):** The patient's age and gender statistically align with the diagnosis.

**VERDICT RULES:**
- If ANY hard gate returns FAIL, or ANY weighted dimension scores a 1, the verdict is **DISCARD**.
- If the hard gates PASS and the weighted dimensions are mostly 3s (but fixable), the verdict is **REVISE**.
- Only if the hard gates PASS and the weighted dimensions are predominantly 5s can the verdict be **APPROVE**.

**OUTPUT FORMAT:**
Take a paragraph to think step-by-step (Chain of Thought) about the case, using web search if needed. 
Then, output your final verdict as a raw JSON object exactly matching this schema:

{
  "case_id": "the case_id from the input",
  "evaluator": "Perplexity",
  "verdict": "APPROVE, REVISE, or DISCARD",
  "reason": "1-sentence summary of the decision",
  "suggested_revisions": ["list of exact changes needed if REVISE", "leave empty otherwise"]
}

[PASTE YOUR CASE JSON HERE]
