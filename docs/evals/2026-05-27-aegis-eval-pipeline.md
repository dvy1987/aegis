# Eval Pipeline: Aegis

## System Overview
Aegis is a 12-agent self-improving swarm designed to draft health insurance appeal letters. 
Maturity Stage: 4 (Continuous eval with autonomous self-improvement loops).
Critical Outputs: Drafted appeal letters, intermediate agent research summaries, and evidence gap lists.

## Evaluator Stack

### Layer 1: Deterministic Evaluators (Fast/Cheap)
- **Safety Gate (Regex/Pattern Check):** Fails if specific PII patterns (SSN, medical record IDs) are detected.
- **Disclaimer Check (String Match):** Fails if exact disclaimer "draft for review - not legal or medical advice" is missing.
- **Length Constraint:** Alerts if response is < 150 words or > 2000 words.
- **Tool-Call Validation:** Ensures formatting of tools (e.g. searching the corpus) is syntactically valid JSON.

### Layer 2: Statistical Evaluators (Metrics/Trends)
- **Retrieval Recall:** Ensures queries return relevant policy documents (measured against known golden doc sets).
- **Latency Distribution:** Tracks average draft time; alerts if > 45 seconds.
- **Token Usage / Cost:** Track token usage per appeal. Alerts if cost > $1.50 per appeal.
- **Bleu/Rouge vs. Templates:** Alerts if the generated letter is identical to standard templates without specific adaptation.

### Layer 3: LLM-as-Judge Evaluators (Nuanced/Expensive)
- **Rubric:** `docs/evals/2026-05-27-aegis-appeal-rubric.md`
- **Judge Model:** GPT-5 or Claude 4 (Different from drafting model).
- **Sampling Rate:** 
  - 100% on nightly benchmark run (12-case MVP or 100-case Full Plan).
  - 100% during autonomous self-improvement proposals (Pairwise mode).
  - 30% for live production inferences.
- **Cost Estimate:** ~$0.15 per eval call given CoT prompts.

## Checkpoints (Multi-Step Validators)
Because Aegis uses a 12-agent swarm, cascade dependency is a critical failure mode.
1. **Medical Record Intake Gate:** Validates that the parsed context contains a patient condition and an insurer name before passing to strategy agents.
2. **Policy Retrieval Gate:** Validates that at least one relevant corpus document was successfully retrieved. If zero results, halt before drafting.
3. **Drafting Gate:** Validates internal consistency before passing to the final polishing/formatting agent.

## Dataset
| Split | Size | Description | Source |
|---|---|---|---|
| **Happy Path** | 40 cases | Representative, winnable cases with complete facts | CMS / KFF public examples (synthesized) |
| **Edge Cases** | 30 cases | Highly sparse denial letters, missing records | Constructed edge cases |
| **Adversarial** | 15 cases | Cases requesting Medicaid/Medicare appeals (Out of Scope) | Synthetic |
| **Known Bad** | 15 cases | Letters specifically engineered to violate safety, hallucinate facts, or contradict themselves | Synthetic |

## CI/CD Integration
- **Pre-merge Gate (PRs):** Deterministic (100%) + Statistical (100%) + LLM Judge (12-case benchmark). Must pass all hard gates. No dimension drop > 10% from baseline.
- **Autonomous Promotion Gate:** When an agent proposes a prompt/playbook update, it is scored against the benchmark in Pairwise comparison against the baseline. If it wins or ties, it promotes. If it fails, rollback.
- **Nightly Run:** Full suite execution against the 100-case benchmark (Part B). Evaluates all "Known Bad" cases to prove the judges still catch failures.

## Baselines and Alerts
- **Baselines:** Established during Day 7 (MVP benchmark run).
- **Regression:** Any quality dimension score dropping >10% from the baseline.
- **Alerts:** Grounding < 4.0; Safety Failures > 0; Internal Consistency Failures > 0.
