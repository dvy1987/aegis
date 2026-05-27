# Project Constitution
Version: 1 | Date: 2026-05-27 | Status: Active

## C-1 Testing
- C-1.1 Backend services and plumbing MUST have ≥ 80% unit test coverage. Rationale: Prevents basic regressions during rapid hackathon iteration.
- C-1.2 AI agent prompts and playbooks MUST NOT be promoted without passing the AlphaEval rubric hard gates on a held-out dataset. Rationale: Prevents unsafe or hallucinated output from reaching the user.
- C-1.3 Every LLM Judge MUST pass a Cohen's κ ≥ 0.6 calibration gate against human labels before its score counts for auto-promotion. Rationale: Ensures the Learning Coordinator isn't optimizing against a broken rubric.

## C-2 Security & Privacy
- C-2.1 Code, tests, evals, and traces MUST NOT contain any Protected Health Information (PHI). Rationale: Legal and ethical hard boundary; synthetic cases only.
- C-2.2 API Keys (Gemini, Phoenix, GCP) MUST NOT be committed to version control and MUST be loaded exclusively via `.env`. Rationale: Prevents credential leaks in a public repository.

## C-3 Performance & Accessibility
- C-3.1 All UI motion transitions MUST default to 400ms and use soft easing curves (`easeOut`). Rationale: Ensures a calm, dignified user experience.
- C-3.2 The UI MUST respect `prefers-reduced-motion: reduce`. Rationale: Non-negotiable accessibility requirement.
- C-3.3 The UI MUST meet WCAG 2.2 AA color contrast minimums and support full keyboard navigation. Rationale: Non-negotiable accessibility requirement.
- C-3.4 User-facing copy MUST be written at ~8th-grade reading level (Flesch reading ease ≥ 60) without insurance jargon. Rationale: Users are stressed and likely lack healthcare system expertise.

## C-4 Dependencies
- C-4.1 Vector Databases (Pinecone, Milvus, Qdrant, etc.) MUST NOT be added to the project. Rationale: Over-engineering for a local corpus; BM25 is sufficient.
- C-4.2 New runtime dependencies MUST NOT be added without explicit PM approval. Rationale: Prevents dependency bloat and maintains architecture lock.

## C-5 Observability
- C-5.1 All agent execution traces MUST be instrumented via `openinference-instrumentation-google-adk` and sent to Phoenix Cloud. Rationale: The Phoenix MCP integration is the load-bearing feature of the project demo.

## C-6 Migration & Rollback
- C-6.1 The Learning Coordinator MUST trigger an instant auto-rollback (demotion) if the swarm's composite score drops >10% over any 10-run rolling window. Rationale: Circuit breaker against reward hacking and overfitting.

## C-7 Documentation
- C-7.1 Any change that modifies agent behavior, architecture, or project strategy MUST be logged via the `memory-decision` or `memory-capture` skill. Rationale: Preserves project context across sessions.
- C-7.2 Any change to a skill MUST update `SKILL-OUTPUTS.md`. Rationale: Maintains an immutable ledger of agent actions.

## Amendments
- 2026-05-27: Initial draft (v1) created by Droid based on PRD, AGENTS.md, and Design Brief invariants.
