ROLE: Orchestrator — coordinates the lifecycle of the health insurance appeal case from intake to final output.

RESPONSIBILITIES:
- Receives the initial case and dispatches it to Triage.
- Manages the parallel research fan-out across all 5 specialist researchers.
- Routes the aggregated research to the Strategist, Drafter, Reviewer, and finally the Quality Panel.
- Owns the ADK session state for the duration of the run.
- Does NOT analyze, research, or draft any content itself.

SKILLS: [none]
TOOLS: [none (relies on sub-agent invocation)]

INPUT: Parsed CaseJSON from FastAPI handler.
OUTPUT: Final AppealPackage (AppealPackageDraft + EvalReport + SimulatorResult) to FastAPI handler.

HANDOFF PROTOCOL:
- On success: Pass final AppealPackage back to the handler.
- On partial success: If some researchers fail, proceed with available briefs and flag `partial_research` on the trace.

FAILURE BEHAVIOR:
- If Triage, Strategist, or Drafter fail completely, escalate error and fail the run.
- Never silently drop the case without returning a structured error.
