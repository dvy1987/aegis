# Arize Track — Hackathon Requirements Assessment

**Date:** 2026-06-07  
**Scope:** General challenge requirements + Arize partner track specifics.  
**Explicitly excluded from this assessment:** whether v1 product flows run through the ADK agent reasoning loop (documented separately in [plans/2026-06-07-aegis-v1-adk-migration-plan.md](plans/2026-06-07-aegis-v1-adk-migration-plan.md)).

---

## Summary

| Area | Verdict |
|---|---|
| Gemini 3 as the brain | **Met** |
| Partner MCP (meaningful, runtime) | **Strong** |
| Move beyond chat / multi-step / human oversight | **Met** |
| OpenInference + Phoenix Cloud tracing | **Partial** |
| Phoenix MCP runtime self-introspection | **Strong** |
| Evaluations on traces (LLM-as-judge) | **Strong** |
| Self-improvement from observability (bonus) | **Strong** |
| Code-owned runtime (Cloud Run) | **Met** |
| Hosted project URL | **Met** |
| Public repo + detectable license | **Met** (verify GitHub About shows Apache-2.0) |
| README accuracy for judges | **Stale** |

**Bottom line:** The Arize-track technical story (MCP, evals, self-improvement) is strong. Submission gaps are mostly operational (README freshness, live deploy env for citations). Tracing richness for LLM calls is thinner than it appears because raw `google.genai` calls are not auto-instrumented today.

  What's solidly satisfied

  Partner MCP — the centerpiece, and it's real. backend/app/aegis_v1/phoenix_mcp.py launches 
  @arizeai/phoenix-mcp over stdio (npx -y @arizeai/phoenix-mcp), calls the get-spans and
  get-span-annotations tools, filters to the case's slice, and feeds the laundered signal back into drafting
   via phoenix_mcp_lookup (backend/app/aegis_v1/tools.py ~L348). This is exactly the track's requirement: 
  "query its own traces… as tools at runtime." MCP-first with a REST fallback. There's even a counterfactual
   toggle (PHOENIX_MCP_ENABLED=false) to show quality collapse without it. This is stronger than most
  submissions will be.

  LLM-as-judge evals. backend/app/evals/part_a/panel.py runs 6 weighted LLM judges plus deterministic 
  safety/citation gates, and writes annotations back onto the Phoenix spans
  (backend/app/evals/part_a/recorder.py log_span_annotations_dataframe). Directly satisfies "run evaluations
   on your traces."

  Self-improvement loop (the bonus). The reflection/optimizer (backend/app/learning/reflection_client.py) 
  consumes laundered Phoenix annotations and proposes new prompts/playbooks, scored as Phoenix experiments
  and promoted under human approval. This is the headline "uses its own observability data to improve over
  time."

  Gemini + Cloud Run + traces to Phoenix Cloud. Gemini 3 confirmed; both services deployed
  (aegis-v1-api-…run.app, aegis-frontend-…run.app); telemetry exports to Phoenix Cloud with the API key
  mounted from Secret Manager.

  License. LICENSE is Apache 2.0 at repo root (GitHub auto-detects this and shows it in About — just confirm
   the repo is public).

  Gaps and risks (prioritized, all fixable, none ADK-related)

  1. Demo video — REQUIRED, not done. No ~3-min video artifact exists; current-state lists "record Devpost
     video" as pending. This is a hard submission requirement.

  2. README is stale and will hurt judging. README.md Status section still says "Pre-build planning… No 
     code yet." (L157) and the repo-structure section marks eval/, playbooks/, scripts/ as "(TBD)". A
     judge reading the repo would be misled. Update before submission.

  3. Tracing richness caveat (related to, but separable from, ADK). OpenInference is installed, but only
     the google-adk instrumentor — and the live drafting/judging flows call raw google.genai, which that
     instrumentor doesn't capture. So the auto-traced LLM-call content is thinner than it looks; what
     reaches Phoenix is mostly the app-level recorder spans + annotations. "Meaningful use of tracing" is
     explicitly judged. Quick, ADK-independent win: add openinference-instrumentation-google-genai (the
     track even lists it) so the raw Gemini calls get traced. Note: this would also start capturing
     denial-letter text in prompts — handle the content-capture/PHI setting at the same time (the issue
     from earlier today).

  4. citations_used: 0 risk undermines the eval/self-improvement demo. Per current-state, live /v1/appeal
     returns zero citations unless VERTEX_SEARCH_* is wired into Cloud Run. Without citations the judges
     hard-gate and the composite collapses — which would make the eval and learning-loop demo look broken.
     Verify the Vertex AI Search env is set on the deployed service before recording.

  5. External submission mechanics — confirm the GitHub repo is public, the Arize track is selected on
     Devpost, and the Devpost form is complete. Can't verify these from the repo.

  One nuance on "Google Cloud Agent Builder"

  The general challenge says "built with Google Cloud Agent Builder," but the Arize track explicitly 
  overrides this: "The visual Agent Builder alone is not supported for tracing integration… You must
  instrument your code directly" and lists Cloud Run as an accepted code-owned runtime. The project uses
  Cloud Run, so this is satisfied for your chosen track — not using the visual Agent Builder is correct
  here, not a gap.

  Net: the hard technical requirements for the Arize track (Gemini, MCP runtime introspection, evals,
  self-improvement, Cloud Run, license) are met or strong. The real exposure is operational: demo video, 
  stale README, the tracing-depth quick win, and the citations env on the live deploy. Want me to fix the
  README and add the google-genai instrumentor (with the PHI-safe capture setting) as two small,
  ADK-independent changes?
  
  Would switching to ADK completely fix tracing richness?

  Mostly yes — but only if the LLM calls actually run through ADK Runner, not just if you define ADK 
  agents.

  Right now you have openinference-instrumentation-google-adk installed, but the live flows (drafter,
  simulator, judges, reflector) call google.genai directly. The ADK instrumentor doesn't see those calls.
  That's why tracing looks thin.

  If you migrate per the hybrid plan — each LLM step becomes an LlmAgent invoked via Runner — the ADK
  instrumentor would trace them: model name, tokens, agent/tool structure in Phoenix. That fixes the
  richness gap for those calls.

  Three caveats:

  1. Defining agents isn't enough. root_agent already exists but /appeal and /showcase never invoke it.
     The fix is routing real traffic through Runner, not adding more agent definitions.

  2. Not everything becomes an LLM span. Deterministic Python (regex case_parser, score_outcome, safety
     gates) only shows up as ADK workflow/tool steps if you wrap them as ADK steps. That's fine — judges
     care about LLM trace richness, and you'd get that.

  3. PHI/content capture flips on. ADK tracing + OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true
     (currently set) means denial-letter text in prompts would start appearing in Phoenix. For /appeal
     that's a real PHI risk. Turn content capture off (or gate it) as part of the ADK migration.

  For the hackathon narrative, full ADK migration is the stronger story (fixes tracing and satisfies "built
   on ADK"). 
   
   ------ Appendix A: Requirements as mentioned in competition page
   
   
   About the challenge
AI that doesn't just provide answers—it helps you take action.
Building Agents for Real-World Challenges is your opportunity to move beyond the chatbot and into the world of agents that accomplish tasks for you. This hackathon is designed for every level of technical builder: whether you are writing your first script or architecting complex systems, this is your chance to build an agent that can reason, plan, and execute tasks under your oversight.
Built with Gemini’s advanced reasoning and our technology partners' solutions, you will create agents that help people get more done. You provide the logic; Gemini provides the brain; our partners provide the superpowers.
Turn your ideas into agents that solve real-world problems.
 
Partners
Six partner tracks are now live. Pick one and build with their MCP server:
Arize
The "Partner Bucket" System
There are three identical prize buckets—one for each of our featured partner tracks. Instead of everyone competing for one giant pile of money, you are competing within the specific "bucket" of the partner technology you used.
How to Qualify
Pick a Partner: Choose the partner technology that best fits the mission you want to accomplish.
Build Your Agent: Create your agent—built with Gemini 3—using Google Cloud Agent Builder. Integrate the partner’s Model Context Protocol (MCP) server to give your agent the superpowers to finish the job.
Win Your Track: You’ll be judged specifically against other builders within that same partner category.
 
Examples of challenges your agent can solve:
2026 World Cup: Build an agent that solves a real-world challenge for the 2026 World Cup! Whether your agent automates fan logistics, assists local businesses in managing tourist surges, or powers a fully automated fantasy league, we want to see how AI can elevate the beautiful game.
Financial Services: Build an agent that solves a real-world problem in the financial sector! Whether your agent automates real-time fraud detection, streamlines complex loan workflows, or executes personalized wealth management, we want to see how AI can drive precision and trust in the modern economy.
Brick-and-Mortar Retail: Build an agent that solves a real-world challenge for brick-and-mortar malls! Whether your agent provides real-time shopper navigation, automates hyper-local tenant campaigns, or streamlines facility operations, we want to see how AI can bridge the gap between digital convenience and physical retail.
Requirements
The Challenge
Your mission is to engineer a functional agent that solves a real-world challenge—specifically targeting your work, personal life, hobbies, or daily routines. We want to see how AI can tackle real-world problems.
Your Goals:
Move Beyond Chat: Your agent shouldn't just answer questions. It should use tools and capabilities to accomplish tasks (e.g., managing a local database, automating a hobbyist workflow, or interacting with a live web service).
The Multi-Step Mission: Build a system that can handle complex goals. Your agent should be able to plan the steps and use the tools at its disposal to finish the job, while keeping you in control.
Partner Power: Your solution must demonstrate a meaningful integration with at least one participating partner’s solution using MCP to give your agent its "superpowers."
How to Build:
Google Cloud Agent Builder: Ideal for rapid prototyping, building, and scaling. Use this low-code, high-power environment to build and orchestrate agents with grounding in your own data.
 
What to Build
💥 Build a functional agent—powered by Gemini and Google Cloud Agent Builder—that integrates a Partner Entity’s MCP server to solve a real challenge.
 
What to Submit
Include a URL to the hosted Project
Include a URL to your open-source code repository for judging and testing. 
The repository must be public and include a complete open source license file. This license should be detectable and visible at the top of the repository page (in the About section)
Include a ~3 minute demo video
Select which track you’ll be submitting to
Your completed Devpost submission form
Judging Criteria
Technological Implementation
Does the interaction with Google Cloud and Partner services demonstrate quality software development?
Design
Is the user experience and design of the project well thought out?
Potential Impact
How big of an impact could the project have on target communities?
Quality of the Idea
How creative and unique is the project?
Google Cloud Agent Builder: Ideal for rapid prototyping, building, and scaling. Use this low-code, high-power environment to build and orchestrate agents with grounding in your own data.
About Arize
Arize is the single platform built to help you accelerate development of AI apps and agents – then perfect them in production. Arize AX is an AI engineering platform focused on evaluation and observability. It helps AI engineers and AI product managers develop, evaluate, iterate and observe and monitor AI applications and agents. Arize helps enterprises increase their speed in building AI agents and ensure effectiveness for those outcomes that they can trust in production environments.
Build Gemini Agents with Full Observability and Self-Introspection via MCP
Ship agents that do more than run.  Ship agents that can self improve. With Arize Phoenix, your Gemini-powered agent gets production-grade tracing from day one, plus the ability to query its own traces, prompts, datasets, and experiments as tools at runtime via the Phoenix MCP server. Every decision your agent makes becomes inspectable, evaluable, and improvable.
We'll evaluate submissions based on technical implementation, meaningful use of tracing and MCP, quality of the agent's self-improvement loop, and overall impact.
Here are some guidelines to get you started:
The Arize track requires a code-owned agent runtime — Gemini CLI, Gemini Enterprise Agent Platform SDK, Google ADK, Agent Runtime, or Cloud Run. The visual Agent Builder alone is not supported for tracing integration. You must be able to instrument your code directly.
Instrument your agent with OpenInference. Auto-instrumentors exist for Google ADK, Agent Platform, Google GenAI, LangChain, LlamaIndex and many other frameworks.
Send traces to Phoenix Cloud (free SAAS) or self-hosted Phoenix
Configure the Phoenix MCP server in your agent so it can introspect its own operational data at runtime
Run evaluations on your traces with LLM-as-a-Judge or code evals to demonstrate quality
Bonus points for agents that use their own observability data to improve over time
How do I get started?
The fastest path is a free Phoenix Cloud account. Grab your API key, pip install an OpenInference instrumentor, and you're tracing in under five minutes. Phoenix is fully open-source, so you can also self-host if you prefer.
For the MCP integration, @arizeai/phoenix-mcp runs via npx and drops into any MCP client config — including Gemini CLI's settings.json.
Resources
Phoenix Cloud — Free tier, hosted Phoenix
Phoenix on GitHub — Open-source, self-hostable
Phoenix documentation — Tracing, evals, datasets, experiments, prompts
Phoenix MCP Server guide — Runtime introspection via MCP
OpenInference on GitHub — OpenTelemetry-compatible auto-instrumentors and utilities
Instrumentors for Gemini / Agent Platform / ADK:
openinference-instrumentation-google-adk — For Google ADK agents
openinference-instrumentation-vertexai — For Gemini Enterprise Agent Platform SDK and Gemini via generative_models
openinference-instrumentation-google-genai — For the unified google-genai SDK
Quickstarts: get up and running fast
https://github.com/Arize-ai/gemini-hackathon — End-to-end example: traced Gemini agent + Phoenix MCP + evaluations
Agent Platform (Gemini) tracing guide — Step-by-step setup
Phoenix LLM-as-a-Judge evals — Add evaluation pipelines to your submission
