# Graph Report - .  (2026-05-30)

## Corpus Check
- 182 files · ~124,851 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 715 nodes · 1046 edges · 50 communities (33 shown, 17 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 166 edges (avg confidence: 0.8)
- Token cost: 616,552 input · 108,800 output

## Community Hubs (Navigation)
- [[_COMMUNITY_V1 Pipeline & Schemas|V1 Pipeline & Schemas]]
- [[_COMMUNITY_Part A Judge Panel (code+tests)|Part A Judge Panel (code+tests)]]
- [[_COMMUNITY_Case Generator CLI & Config|Case Generator CLI & Config]]
- [[_COMMUNITY_Architecture & Swarm Design|Architecture & Swarm Design]]
- [[_COMMUNITY_Self-Improvement Loop & Autonomy Ladder|Self-Improvement Loop & Autonomy Ladder]]
- [[_COMMUNITY_ScopeSafety Constraints & Plans|Scope/Safety Constraints & Plans]]
- [[_COMMUNITY_AlphaEval Rubric & Eval Discipline|AlphaEval Rubric & Eval Discipline]]
- [[_COMMUNITY_ADK Agents & Appeal Artifacts|ADK Agents & Appeal Artifacts]]
- [[_COMMUNITY_Case Gen Producer Agents (Vertex)|Case Gen Producer Agents (Vertex)]]
- [[_COMMUNITY_Case Gen Critic Functions|Case Gen Critic Functions]]
- [[_COMMUNITY_CriticEvaluator Roster|Critic/Evaluator Roster]]
- [[_COMMUNITY_Judge Clients & Regulatory Corpus|Judge Clients & Regulatory Corpus]]
- [[_COMMUNITY_FrontendUX & Deployment ADRs|Frontend/UX & Deployment ADRs]]
- [[_COMMUNITY_Frontend Components|Frontend Components]]
- [[_COMMUNITY_Agents, Prompts & Evaluator Disagreement|Agents, Prompts & Evaluator Disagreement]]
- [[_COMMUNITY_E2E Server Tests|E2E Server Tests]]
- [[_COMMUNITY_Dev Launcher (PowerShell)|Dev Launcher (PowerShell)]]
- [[_COMMUNITY_MVP Scope Critics & Envelope|MVP Scope Critics & Envelope]]
- [[_COMMUNITY_Phoenix MCP Spike|Phoenix MCP Spike]]
- [[_COMMUNITY_Frontend Layout|Frontend Layout]]
- [[_COMMUNITY_Agent Integration Test|Agent Integration Test]]
- [[_COMMUNITY_Dummy Test|Dummy Test]]
- [[_COMMUNITY_PostCSS Config|PostCSS Config]]
- [[_COMMUNITY_Next Config|Next Config]]
- [[_COMMUNITY_ESLint Config|ESLint Config]]
- [[_COMMUNITY_Evals Package Init|Evals Package Init]]
- [[_COMMUNITY_Judge Panel Init|Judge Panel Init]]
- [[_COMMUNITY_Student Case Packet|Student Case Packet]]
- [[_COMMUNITY_GCP Completions Join|GCP Completions Join]]
- [[_COMMUNITY_PM Working Agreement|PM Working Agreement]]
- [[_COMMUNITY_PanelReport schema|PanelReport schema]]
- [[_COMMUNITY_SynthProvenance schema|SynthProvenance schema]]
- [[_COMMUNITY_AppealDifficulty schema|AppealDifficulty schema]]
- [[_COMMUNITY_Feedback model|Feedback model]]
- [[_COMMUNITY_No Surprises Act|No Surprises Act]]
- [[_COMMUNITY_Dummy unit test|Dummy unit test]]
- [[_COMMUNITY_Deferred Memory|Deferred Memory]]

## God Nodes (most connected - your core abstractions)
1. `_run_critic()` - 23 edges
2. `Final Arbiter` - 19 edges
3. `generate_one_case()` - 16 edges
4. `OfflineHeuristicJudgeClient` - 15 edges
5. `run_aegis_v1_pipeline()` - 14 edges
6. `run_panel()` - 14 edges
7. `JudgeResult` - 14 edges
8. `generate_one_case` - 14 edges
9. `Orchestrator Agent System Prompt` - 13 edges
10. `Learning Coordinator (background meta-agent)` - 13 edges

## Surprising Connections (you probably didn't know these)
- `AppealDifficulty evaluator` --semantically_similar_to--> `run_panel (Part A judge panel)`  [INFERRED] [semantically similar]
  backend/app/case_generator/prompts/c_appeal_difficulty.txt → backend/app/evals/part_a/panel.py
- `Medical Necessity Researcher System Prompt` --semantically_similar_to--> `BM25 Spike (main)`  [INFERRED] [semantically similar]
  backend/src/prompts/medical_necessity_v1.md → backend/spike_bm25.py
- `ADR-001 Use Google ADK` --references--> `Phoenix MCP Server (@arizeai/phoenix-mcp)`  [EXTRACTED]
  docs/adr/ADR-001-google-adk-agent-framework.md → backend/spike_mcp.py
- `Aegis — Self-Improving Multi-Agent Appeals System` --conceptually_related_to--> `Phoenix MCP Server (@arizeai/phoenix-mcp)`  [EXTRACTED]
  docs/memory/project-index.md → backend/spike_mcp.py
- `aegis_v1 root_agent` --implements--> `Google ADK (Agent Development Kit)`  [INFERRED]
  backend/tests/unit/agent/test_aegis_v1_agent.py → docs/adr/ADR-001-google-adk-agent-framework.md

## Hyperedges (group relationships)
- **Synthetic Case Generation Pipeline (plan -> draft -> contextualize -> diversify)** — p1_scenario_planner_scenarioplanner, p2_denial_drafter_denialletterdrafter, p3_clinical_writer_clinicalcontextwriter, p4_adversarial_diversifier_adversarialdiversifier, p5_stylistic_diversifier_stylisticdiversifier [INFERRED 0.85]
- **Synthetic-Case Critic Panel (multi-dimension evaluators with hard gates)** — c_denial_logic_deniallogiccritic, c_diagnosis_treatment_match_diagnosistreatmentmatchcritic, c_overall_tone_overalltonecritic, c_date_sanity_datesanitycritic, c_citation_traceability_citationtraceabilitycritic, c_contradiction_hunter_contradictionhunter, c_scenario_realism_scenariorealismcritic, c_legal_auditor_legalauditor, c_safety_redactor_safetyredactor [INFERRED 0.85]
- **Competency-Gated Autonomy Ladder (Apprentice/Journeyman/Master)** — readme_self_improvement_loop, readme_learning_coordinator, readme_phoenix_mcp_loadbearing [INFERRED 0.85]
- **Aegis v1 seven-tool deterministic appeal pipeline** — tools_case_parser, tools_corpus_retrieval, tools_phoenix_mcp_lookup, tools_playbook_loader, tools_drafter, tools_self_check, tools_simulator [EXTRACTED 1.00]
- **Synthetic case generator critic panel (shared envelope)** — prompts_critic_envelope, prompts_c_financial_auditor, prompts_c_clinical_realism, prompts_c_insurer_voice, prompts_c_demographic_validator, prompts_c_scope_guard [INFERRED 0.85]
- **Part A judge panel: hard gates plus weighted quality dimensions** — panel_run_panel, panel_quality_weights, schemas_appealpackage, panel_evaluator_disagreement [EXTRACTED 0.85]
- **Producer-critic per-stage generation swarm** — pipeline_generate_one_case, pipeline_scenario_planner_stage, pipeline_denial_drafter_stage, pipeline_clinical_writer_stage, pipeline_final_panel [EXTRACTED 0.85]
- **Part A panel run: pipeline to teacher packet to judges** — cli_run_one, aegis_v1_pipeline_run_aegis_v1_pipeline, teacher_packet_build_teacher_grading_packet, panel_run_panel [EXTRACTED 0.85]
- **Controlled regulatory corpus authorities** — corpus_erisa_503, corpus_cigna_medical_necessity, corpus_nsa_surprise_billing, corpus_mhpaea_parity [INFERRED 0.75]
- **Aegis Part B agent pipeline (triage to judge)** — prompt_triage, prompt_medical_necessity, prompt_legal_researcher, prompt_policy_detective, prompt_insurer_intelligence, prompt_precedent_miner, prompt_strategist, prompt_drafter, prompt_adversarial_reviewer, prompt_orchestrator [EXTRACTED 1.00]
- **Five parallel-fan-out researchers** — prompt_medical_necessity, prompt_legal_researcher, prompt_policy_detective, prompt_insurer_intelligence, prompt_precedent_miner [EXTRACTED 1.00]
- **Phoenix MCP load-bearing observability thesis** — phoenix_mcp, prompt_insurer_intelligence, concept_openinference_adk, adr001_google_adk [INFERRED 0.85]
- **Part B runtime appeal pipeline (research fan-out -> strategy -> draft -> review -> eval)** — orchestrator_agent, triage_agent, insurer_intelligence_agent, strategist_agent, drafter_agent, adversarial_reviewer_agent, quality_judge_panel, outcome_simulator [EXTRACTED 1.00]
- **Anti-Cheating Firewall: Student blind, Teacher graded, Learner trace-only** — anticheating_firewall, student_case_packet, teacher_grading_packet, learning_coordinator [EXTRACTED 1.00]
- **AlphaEval rubric principles realized in Aegis judging** — alphaeval_2026, binary_hard_gates, forced_anchor_scoring, cot_before_score [EXTRACTED 1.00]
- **Self-Improvement Loop (Phoenix-driven autonomous learning)** — learning_coordinator, phoenix_mcp, skillopt, anti_cheating_firewall, autonomy_ladder [EXTRACTED 1.00]
- **AlphaEval 2026 Compliance Across Evaluators** — alphaeval_2026, eval_rubric_v2, gumloop_evaluator, part_a_judge_panel, case_generator_swarm [EXTRACTED 1.00]
- **Synthetic Case Generation + Evaluation Pipeline** — case_generator_swarm, gumloop_evaluator, flaws_are_features, claude_on_vertex_critic [EXTRACTED 1.00]
- **Part A Independent Judge Panel (j1-j7)** — j1_safety_scope, j2_faithfulness_hallucination, j3_grounding, j4_case_specific_rebuttal, j5_evidence_completeness, j6_appeal_vector_capture, j7_persuasive_coherence [INFERRED 0.85]
- **Competency-Gated Autonomy Stages** — stage_apprentice, stage_journeyman, stage_master [EXTRACTED 0.75]
- **Synthetic Case Generation & Approval Lifecycle** — case_generator_swarm, finalassembly_minipanel, gumloop_swarm [EXTRACTED 0.75]
- **Gumloop Critic Swarm (17 critics + arbiter)** — clinical_critic, tone_critic, llm_tell_detector, financial_auditor, legal_auditor, contradiction_hunter, demographic_validator, dx_tx_match_evaluator, insurer_voice_evaluator, denial_logic_evaluator, date_sanity_evaluator, citation_traceability_evaluator, scope_guard, safety_redactor, realism_assessor, appeal_difficulty_assessor, flaw_injection_verifier, final_arbiter [EXTRACTED 0.95]
- **Tier 1 Hard Gates (FAIL = DISCARD)** — contradiction_hunter, scope_guard, safety_redactor, dx_tx_match_evaluator, demographic_validator [EXTRACTED 0.95]
- **Aegis Dev Stack (v1 + swarm backends + frontend)** — dev_launcher_script, backend_v1_service, backend_swarm_service, frontend_home_page [EXTRACTED 0.85]

## Communities (50 total, 17 thin omitted)

### Community 0 - "V1 Pipeline & Schemas"
Cohesion: 0.06
Nodes (63): Run the deterministic seven-tool v1 flow for local smoke tests., run_aegis_v1_pipeline(), AppealDraft, AppealPackage, CitationCheck, CitationHit, ParsedCase, PhoenixSummary (+55 more)

### Community 1 - "Part A Judge Panel (code+tests)"
Cohesion: 0.06
Nodes (50): _appeal_package(), _case_obj(), test_appeal_vector_capture_rewards_flaw_aware_letter(), test_appeal_vector_score_one_is_promotion_blocker(), test_panel_runs_offline_and_returns_all_dimensions(), test_safety_scope_gate_fails_missing_disclaimer(), test_student_packet_excludes_answer_key(), test_teacher_packet_includes_answer_key() (+42 more)

### Community 2 - "Case Generator CLI & Config"
Cohesion: 0.06
Nodes (49): main(), _next_free_index(), _parser(), CLI entrypoint for the Aegis synthetic case generation swarm.  Examples:   uv ru, banned_filter_version(), joint_constraints_text(), load_banned(), load_denial_patterns() (+41 more)

### Community 3 - "Architecture & Swarm Design"
Cohesion: 0.06
Nodes (49): ADK session.state shared blackboard with namespaced keys, ADR-002: Phoenix Cloud + MCP as load-bearing observability layer, Lean composite (5 runtime + 1 offline) alternative — rejected, 12-agent swarm revisit triggers (Day 10, A5, Day 15, slippage), ADR-004: Part B uses 12-agent composite swarm, Adversarial Reviewer (Red Team) Agent, Aegis System Architecture (source-of-truth blueprint), agent-system-architecture skill (+41 more)

### Community 4 - "Self-Improvement Loop & Autonomy Ladder"
Cohesion: 0.07
Nodes (45): A4 Go/No-Go: Phoenix MCP Latency Passed, ADR-005: Adopt google-agents-cli for backend dev lifecycle, Aegis — Self-Improving Multi-Agent Appeals System, Agent Handoffs Log, Skill routing rule (ADK work to agents-cli skills), Anti-Cheating Firewall (Teacher vs Student), Assumption Map — Aegis PRD + Plan, Auto-Demotion Circuit Breaker (+37 more)

### Community 5 - "Scope/Safety Constraints & Plans"
Cohesion: 0.06
Nodes (42): agents-cli manifest (temp-backend, adk), Part A MVP (single agent, 12-case benchmark), Part B Full Plan (12-agent swarm, autonomous learning), Safety & Disclosure Rules (no PHI, no invented statutes), Hard Scope Constraints, BM25 retrieval over local markdown (no vector DB), AlphaEval-compliant eval discipline, google-agents-cli dev backbone (+34 more)

### Community 6 - "AlphaEval Rubric & Eval Discipline"
Cohesion: 0.07
Nodes (41): Aegis Dataset Card, AlphaEval 2026 (independent dimensions, binary hard gates, CoT-before-score), AlphaEval 2026 Alignment Plan, Aegis Appeal Letter Eval Rubric v2, Binary hard gates (safety + hallucination, never averaged), Canonical Safety Disclaimer, Synthetic Case Generator Swarm, Case Generator Harness + Claude-on-Vertex Plan (+33 more)

### Community 7 - "ADK Agents & Appeal Artifacts"
Cohesion: 0.09
Nodes (37): ADR-001 Use Google ADK, AdversarialCritique artifact, AppealPackage artifact, AppealPackageDraft artifact, AppealStrategy artifact, CaseJSON input, ClinicalBrief artifact, Google ADK (Agent Development Kit) (+29 more)

### Community 8 - "Case Gen Producer Agents (Vertex)"
Cohesion: 0.06
Nodes (35): _generate_json (Vertex Gemini call), run_clinical_writer, run_denial_drafter, run_realistic_flaw_injector, run_scenario_planner, run_stylistic_diversifier, case_generator pipeline, joint_constraints_text (+27 more)

### Community 9 - "Case Gen Critic Functions"
Cohesion: 0.12
Nodes (32): _client(), critic_appeal_difficulty(), critic_citation_traceability(), critic_clinical_realism(), critic_contradiction_hunter(), critic_date_sanity(), critic_demographic_validator(), critic_denial_logic() (+24 more)

### Community 10 - "Critic/Evaluator Roster"
Cohesion: 0.08
Nodes (31): Appeal Draft Assistant (not legal/medical advice), Appeal Difficulty Assessor (meta-evaluator), Backend Swarm Service (main_swarm), Backend v1 Service (main_v1), Citation Traceability Evaluator, Clinical Realism Critic, Contradiction Hunter, Date Sanity Evaluator (+23 more)

### Community 11 - "Judge Clients & Regulatory Corpus"
Cohesion: 0.08
Nodes (30): _critic_model bias-avoidance limitation, _run_critic, _client judge factory, Part A panel CLI main, _run_one (Part A), Milliman Care Guidelines (MCG), Non-Quantitative Treatment Limitations (NQTL), CRITIC_MODEL self-enhancement-bias choice (+22 more)

### Community 12 - "Frontend/UX & Deployment ADRs"
Cohesion: 0.08
Nodes (29): A4 assumption gate (Phoenix MCP + ADK integration) — PASSED, Accessibility floor (WCAG 2.2 AA, grade-8 reading level), ADR-003: Next.js frontend + Python ADK backend (two Cloud Run services), Reversal of Session 1 Streamlit lock-in, UX as a first-class product pillar, Case generator on GCP via Application Default Credentials, Logical backend split: v1 API (8001) + Swarm API (8002), ADR-006: Multi-service backend topology + GCP generation job (+21 more)

### Community 13 - "Frontend Components"
Cohesion: 0.1
Nodes (20): Button, ButtonProps, Variant, variants, Wordmark(), ArrowRightIcon, ArrowUpRightIcon, CheckIcon (+12 more)

### Community 14 - "Agents, Prompts & Evaluator Disagreement"
Cohesion: 0.09
Nodes (27): AEGIS_V1_INSTRUCTION (weak baseline), aegis_v1 root_agent (ADK), Aegis Swarm FastAPI App, Aegis V1 FastAPI App, Evaluator disagreement detection (simulator vs judges), QUALITY_WEIGHTS (judge dimension weighting), run_panel (Part A judge panel), run_aegis_v1_pipeline (deterministic flow) (+19 more)

### Community 15 - "E2E Server Tests"
Cohesion: 0.15
Nodes (14): log_output(), Test the chat stream functionality., Test the chat stream error handling., Test the feedback collection endpoint (/feedback) to ensure it properly     logs, Log the output from the given pipe., Start the FastAPI server using subprocess and log its output., Wait for the server to be ready., Pytest fixture to start and stop the server for testing. (+6 more)

### Community 16 - "Dev Launcher (PowerShell)"
Cohesion: 0.36
Nodes (7): Start-BackendSwarm(), Start-BackendV1(), Start-Frontend(), Start-StreamingProcess(), Test-Tool(), Write-Err2(), Write-Info()

### Community 17 - "MVP Scope Critics & Envelope"
Cohesion: 0.2
Nodes (10): Aegis MVP Scope (Aetna/Cigna/UHC, commercial, adult), ClinicalRealismCritic, DemographicValidator Critic, DiversityDeltaCritic, FinancialAuditor Critic, InsurerVoiceCritic, LLMTellDetector (hard gate), MatrixCoverageCritic (hard gate) (+2 more)

### Community 18 - "Phoenix MCP Spike"
Cohesion: 0.33
Nodes (4): fetch_traces(), query_traces_sync(), Fetches traces from Phoenix using MCP.          Args:         query: The filter, Synchronous wrapper for fetch_traces.          Args:         query: The filter q

### Community 19 - "Frontend Layout"
Cohesion: 0.33
Nodes (4): display, metadata, mono, sans

## Ambiguous Edges - Review These
- `Frontend Agent Rules` → `Frontend README`  [AMBIGUOUS]
  frontend/README.md · relation: conceptually_related_to

## Knowledge Gaps
- **189 isolated node(s):** `config`, `nextConfig`, `eslintConfig`, `ArrowUpRightIcon`, `CheckIcon` (+184 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Frontend Agent Rules` and `Frontend README`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `_run_one (Part A)` connect `Judge Clients & Regulatory Corpus` to `V1 Pipeline & Schemas`, `Agents, Prompts & Evaluator Disagreement`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `run_aegis_v1_pipeline()` connect `V1 Pipeline & Schemas` to `Part A Judge Panel (code+tests)`, `Judge Clients & Regulatory Corpus`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `Learning Coordinator (background meta-agent)` connect `Self-Improvement Loop & Autonomy Ladder` to `Architecture & Swarm Design`, `AlphaEval Rubric & Eval Discipline`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `OfflineHeuristicJudgeClient` (e.g. with `JudgeResult` and `test_panel_runs_offline_and_returns_all_dimensions()`) actually correct?**
  _`OfflineHeuristicJudgeClient` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `config`, `nextConfig`, `eslintConfig` to the rest of the system?**
  _189 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `V1 Pipeline & Schemas` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._