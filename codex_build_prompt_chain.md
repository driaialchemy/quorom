# Codex Prompt Chain For Building Quorum

## Purpose

Use this prompt chain to build Quorum with Codex or another agentic coding app. It is optimized for:

- efficient token use
- small, verified implementation phases
- minimal nonessential code
- strict adherence to project constraints
- early tests instead of late rewrites
- avoiding architecture drift and speculative abstractions

The chain combines these prompt patterns:

- ABCDE
- Context Manager
- Constraint-Satisfaction
- PB7: Problem Decomposition and Integration
- PB6: Gradual Execution and Output
- ReAct / ART
- PB10 / Chain-of-Verification
- PC1: Sequential Bug Identification and Resolution
- Reflection-Based phase review

## How To Use This Chain

Use one prompt at a time. Do not give Codex the whole chain as one task.

After each prompt, require:

- changed files
- tests run
- test results
- unresolved risks
- confirmation that the next phase has not been started

If a phase fails tests, use the Debug Prompt before continuing.

## Global Build Rules

These rules apply to every prompt in this chain.

```text
Before editing, read the relevant local files. Do not rely on memory.

Follow AGENTS.md exactly.
Use quorum_workflow_design.md as the full product specification.
Use build_conclusions.md as the final build decision document.

Keep the implementation lean. Do not add abstractions unless they remove real duplication, enforce a project rule, or are already called for by the spec.

Do not implement future phases early.
Do not modify unrelated files.
Do not make real LLM, OpenAI, Anthropic, Gemini, DeepSeek, or Snowflake calls in tests.
Do not commit .env or secrets.

Every phase must include focused tests unless explicitly impossible.
Run the relevant tests before finishing the phase.
Report changed files, tests run, results, and risks.
```

---

# Prompt 0: Spec Assimilation And Build Plan

Pattern mix: ABCDE + Context Manager + PB2 + PB7

```text
Action:
Read the Quorum project documents and produce a concise implementation plan. Do not write application code yet.

Background:
This is the Quorum project: an agentic data analyst that turns natural-language questions into Snowflake SQL, executes against TPCH_SF1, critiques results with a multi-model ensemble, arbitrates, and produces a structured insight report.

Read these files first:
- AGENTS.md
- quorum_workflow_design.md
- build_conclusions.md

Constraints:
- Do not edit source code in this step.
- Do not scaffold the project yet unless a tiny planning artifact is necessary.
- Preserve the build order from AGENTS.md, amended by build_conclusions.md.
- Treat LangGraph node return dictionaries only as framework envelopes; no raw business dictionaries inside state fields.
- Maximize build efficiency and minimize bloat.

Details:
Produce a phase-by-phase implementation checklist with:
- files to create or edit
- tests to create or run per phase
- stopping condition for each phase
- risks to watch

Evaluation:
The plan is successful if it is specific enough to execute one phase at a time and does not skip schemas, tests, SQL validation, lazy Snowflake initialization, or shared LLM utilities.
```

Stop after this prompt. Review the plan before continuing.

---

# Prompt 1: Repository Skeleton And Config Hygiene

Pattern mix: ABCDE + Constraint-Satisfaction + PB6

```text
Action:
Create only the repository skeleton and project hygiene files needed before schemas.

Background:
Use the approved Quorum build plan. The codebase should support a Python 3.11+ package with Pydantic v2, LangGraph, Snowflake, Streamlit, and mocked tests.

Constraints:
- Follow AGENTS.md exactly.
- Do not implement schemas, nodes, graph, LLM clients, or Streamlit yet.
- Do not create or commit .env.
- Add .env.example with blank required variables.
- Add .gitignore that excludes .env and common Python artifacts.
- Keep pyproject.toml minimal and aligned with quorum_workflow_design.md.
- Do not add extra dependencies beyond the spec unless essential.

Details:
Create the package and test directory structure expected by the spec:
- quorum/
- quorum/schemas/
- quorum/llm/
- quorum/tools/
- quorum/nodes/
- prompts/
- tests/

Create __init__.py files where needed.

Evaluation:
Run a lightweight command to verify the file structure. If pytest is available, run a no-op collection check only if useful. Report changed files and confirm no future phases were implemented.
```

Stop after this prompt.

---

# Prompt 2: Schemas And AgentState

Pattern mix: PC7 + Constraint-Satisfaction + PB6 + PB10

```text
Action:
Implement only the Pydantic schemas and AgentState, plus focused schema tests.

Background:
The schemas are the foundation for all node boundaries. Use quorum_workflow_design.md Section 6 and AGENTS.md Pydantic conventions.

Constraints:
- Use Pydantic v2.
- Every optional field must default to None.
- Every list field must default to an empty list, preferably with Field(default_factory=list).
- CritiqueResult.confidence_score must validate 0.0 through 1.0.
- QueryPlan.total_steps must equal len(steps).
- InsightReport.generated_at must auto-populate.
- Do not implement LLM clients, tools, nodes, graph, or Streamlit.

Details:
Implement:
- quorum/state.py
- quorum/schemas/plan.py
- quorum/schemas/query.py
- quorum/schemas/critique.py
- quorum/schemas/report.py
- quorum/schemas/__init__.py
- tests/test_schemas.py

Evaluation:
Run:
pytest tests/test_schemas.py -v

Before final response, verify:
- no raw business dicts are used as schema stand-ins
- defaults match the spec
- validation errors are tested
```

Stop after this prompt.

---

# Prompt 3: Prompt Files And Prompt Tests

Pattern mix: Template + Constraint-Satisfaction + PB10

```text
Action:
Create the runtime prompt files and tests that verify their existence and required ending.

Background:
Quorum loads prompts from prompts/*.txt. Prompt text must not be hardcoded in Python node files.

Constraints:
- Do not implement nodes yet.
- Every prompt must end with the required JSON-only instruction:
  "Output strictly valid JSON matching the [SchemaName] schema. No preamble. No markdown fences."
- Use the correct schema name for each prompt.
- Keep prompts concise but complete enough to satisfy quorum_workflow_design.md Section 9.

Details:
Create:
- prompts/planner.txt
- prompts/sql_generator.txt
- prompts/critic.txt
- prompts/arbiter.txt
- prompts/synthesizer.txt
- tests/test_prompts.py

Evaluation:
Run:
pytest tests/test_prompts.py -v

Report changed files and confirm no node logic was implemented.
```

Stop after this prompt.

---

# Prompt 4: Shared LLM Utilities

Pattern mix: Constraint-Satisfaction + PA1 + PB6 + PB10

```text
Action:
Implement shared LLM utility code and tests. Do not implement provider clients yet.

Background:
All LLM clients must share JSON fence stripping, Pydantic validation, retry prompt construction, and common exceptions to avoid drift.

Constraints:
- Do not call real provider APIs.
- Do not implement Anthropic, OpenAI, or Gemini clients yet.
- Keep utilities small and provider-agnostic.
- Use Pydantic v2 validation.

Details:
Implement:
- quorum/llm/utils.py
- relevant exports in quorum/llm/__init__.py if appropriate
- tests/test_llm_utils.py

Utilities should include:
- strip_json_fences(text: str) -> str
- parse_response_model(text: str, response_model: type[BaseModel]) -> BaseModel
- build_retry_prompt or equivalent
- LLMParseError
- RateLimitError if useful now

Evaluation:
Run:
pytest tests/test_llm_utils.py -v

Also run schema tests if imports overlap:
pytest tests/test_schemas.py tests/test_llm_utils.py -v
```

Stop after this prompt.

---

# Prompt 5: LLM Provider Clients

Pattern mix: ABCDE + Constraint-Satisfaction + ReAct/ART + PB10

```text
Action:
Implement the three async LLM provider client modules using the shared utility layer.

Background:
The spec requires a shared async interface:
async def call_llm(system_prompt, user_prompt, response_model, model_string) -> BaseModel

Anthropic client handles both Claude and DeepSeek via Anthropic SDK format.
OpenAI client handles GPT-5.5 only.
Gemini client handles Gemini 3.1 Pro Preview only.

Constraints:
- Do not make real API calls in tests.
- Do not install a DeepSeek SDK.
- DeepSeek must use the Anthropic SDK with base_url.
- DeepSeek model string must be deepseek-v4-pro.
- OpenAI model must be gpt-5.5-2026-04-23 and use reasoning_effort="high".
- Gemini must use google-genai async client.
- Provider clients should not duplicate JSON parsing logic from utils.py.
- Do not implement nodes or graph yet.

Details:
Implement:
- quorum/llm/anthropic_client.py
- quorum/llm/openai_client.py
- quorum/llm/gemini_client.py
- tests for provider parameter construction and mocked responses

Evaluation:
Run the relevant LLM tests and any schema/utility tests they depend on.
Report any SDK API uncertainty explicitly rather than guessing silently.
```

Stop after this prompt.

---

# Prompt 6: SQL Validator

Pattern mix: Constraint-Satisfaction + PC7 + PB10

```text
Action:
Implement deterministic SQL validation/post-processing and tests.

Background:
The SQL Generator LLM is instructed to produce safe Snowflake SQL, but deterministic enforcement is required before execution.

Constraints:
- No LLM calls.
- No Snowflake calls.
- Keep v1 validation simple and explicit.
- Require a single SELECT statement.
- Reject obvious multi-statement SQL.
- Append LIMIT 50 when missing.
- Cap LIMIT above 100.
- Reject fully qualified TPCH table names like SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS.
- Preserve unqualified table names.

Details:
Implement:
- quorum/tools/sql_validator.py
- tests/test_sql_validator.py

Evaluation:
Run:
pytest tests/test_sql_validator.py -v
```

Stop after this prompt.

---

# Prompt 7: Snowflake Client

Pattern mix: ABCDE + Constraint-Satisfaction + PB6 + PB10

```text
Action:
Implement the deterministic Snowflake client with lazy reusable connection and mocked tests.

Background:
The executor will call this client. It must not call LLMs. It must return QueryResult for execution failures rather than raising query exceptions.

Constraints:
- Do not connect to Snowflake at module import time.
- Use lazy singleton connection creation.
- Reuse the connection after creation.
- execute_query must catch all execution exceptions and return QueryResult(success=False, error_detail=...).
- Do not create a new connection per query.
- get_schema_context must return the TPCH_SF1 schema context from the spec, including revenue formula.
- Unit tests must mock Snowflake.
- Do not implement executor node yet.

Details:
Implement:
- quorum/tools/snowflake_client.py
- tests/test_snowflake_client.py

Evaluation:
Run:
pytest tests/test_snowflake_client.py -v
```

Stop after this prompt.

---

# Prompt 8: Planner And SQL Generator Nodes

Pattern mix: PB7 + Constraint-Satisfaction + ReAct/ART + PB10

```text
Action:
Implement only the Planner and SQL Generator nodes with isolated tests.

Background:
Nodes must consume AgentState and return only modified state fields in LangGraph update dictionaries. Business payload values must be Pydantic models.

Constraints:
- Load prompts at module import time.
- Do not hardcode prompt text inside Python node functions.
- Planner uses claude-sonnet-4-6.
- SQL Generator uses claude-sonnet-4-6.
- SQL Generator must call the deterministic SQL validator before returning.
- SQL Generator must increment attempts.
- Do not implement executor, critics, arbiter, step router, synthesizer, or graph yet.
- Mock LLM clients in tests.

Details:
Implement:
- quorum/nodes/planner.py
- quorum/nodes/sql_generator.py
- focused tests in tests/test_nodes.py or separate node test files

Evaluation:
Run the focused node tests plus prior relevant tests.
```

Stop after this prompt.

---

# Prompt 9: Executor Node

Pattern mix: Constraint-Satisfaction + PB6 + PB10

```text
Action:
Implement only the Executor node and tests.

Background:
The Executor is deterministic. It calls snowflake_client.execute_query and returns the QueryResult unchanged.

Constraints:
- Never call an LLM inside Executor.
- Never raise Snowflake execution errors from Executor.
- Return only {"query_result": query_result}.
- Do not implement critics or graph yet.
- Mock snowflake_client in tests.

Details:
Implement:
- quorum/nodes/executor.py
- executor tests

Evaluation:
Run focused executor tests and relevant existing tests.
```

Stop after this prompt.

---

# Prompt 10: Critic Helpers And Critic Nodes

Pattern mix: PB7 + Constraint-Satisfaction + PB10

```text
Action:
Implement shared critic pre-check logic and the three critic nodes with tests.

Background:
Each critic receives the same state and writes to its own critique field. Deterministic pre-checks run before any LLM call.

Constraints:
- Pre-checks must reject failed SQL, zero rows, and all-null columns without LLM calls.
- Row count >= 95 should add a truncation warning to the critic prompt path.
- Critic A uses OpenAI GPT-5.5.
- Critic B uses Gemini 3.1 Pro Preview.
- Critic C uses DeepSeek V4 Pro through Anthropic client.
- Do not implement arbiter or graph yet.
- Mock all LLM clients in tests.

Details:
Implement:
- shared critic helper module if useful
- quorum/nodes/critic_openai.py
- quorum/nodes/critic_gemini.py
- quorum/nodes/critic_deepseek.py
- critic tests, especially pre-checks that prove no LLM call happens

Evaluation:
Run focused critic tests and relevant prior tests.
```

Stop after this prompt.

---

# Prompt 11: Arbiter And Step Router Nodes

Pattern mix: Constraint-Satisfaction + PB7 + PB10

```text
Action:
Implement only the Arbiter and Step Router nodes with tests.

Background:
The Arbiter receives three critiques and decides whether to approve, retry, or gracefully exit. The Step Router advances approved steps and resets per-step fields.

Constraints:
- avg_confidence must be calculated in Python, not by LLM.
- If any critique is missing, treat it as rejection with confidence 0.0.
- If all critics approve but avg_confidence < 0.70, final_approved must be false.
- If attempts >= max_attempts, final_approved must be true for graceful exit.
- Step Router must append approved query_result to all_results.
- Step Router must reset per-step fields to None and attempts to 0.
- Do not implement synthesizer or graph yet.

Details:
Implement:
- quorum/nodes/arbiter.py
- quorum/nodes/step_router.py
- tests for arbitration overrides and step reset behavior

Evaluation:
Run focused tests and relevant prior tests.
```

Stop after this prompt.

---

# Prompt 12: Synthesizer Node

Pattern mix: Constraint-Satisfaction + PB10 + Reflection

```text
Action:
Implement only the Synthesizer node with tests.

Background:
The Synthesizer produces the final InsightReport from approved results and arbitration history. It must also handle empty approved results deterministically.

Constraints:
- If all_results is empty, do not call the LLM. Return a failure-oriented InsightReport and status="failed".
- If prior approved results exist, call Claude Sonnet and synthesize only from approved results.
- Include mandatory caveats about sample data, row limits, and critique flags.
- Attach data_tables, ensemble_summary, generated_at, and models_used.
- Do not implement graph or Streamlit yet.
- Mock LLM client in tests.

Details:
Implement:
- quorum/nodes/synthesizer.py
- synthesizer tests, including empty-results behavior

Evaluation:
Run focused synthesizer tests and relevant prior tests.
```

Stop after this prompt.

---

# Prompt 13: LangGraph Assembly

Pattern mix: EEDP + Constraint-Satisfaction + ReAct/ART + PB10

```text
Action:
Wire the LangGraph graph and public run_agent / stream_agent interfaces.

Background:
All node units should already be implemented and tested. Graph assembly should happen late and should not change node contracts.

Constraints:
- Use AgentState from quorum/state.py.
- Register nodes according to the spec.
- Routing functions must be standalone functions, not lambdas.
- Expose run_agent(question: str) and stream_agent(question: str).
- Use compiled_graph.invoke for run_agent.
- Use compiled_graph.stream for stream_agent.
- Do not implement Streamlit UI yet.
- Prefer the simplest reliable critic parallelism. Use Send API if clean; otherwise use an ensemble_critic node with asyncio.gather, while preserving independent critic behavior.

Details:
Implement:
- quorum/graph.py
- graph tests in tests/test_graph.py

Graph tests must cover:
- happy path
- retry path
- max retries
- multi-step success
- 2-1 critic split
- all critics reject
- empty approved results

Evaluation:
Run:
pytest tests/test_graph.py -v

Then run the full current suite:
pytest tests/ -v
```

Stop after this prompt.

---

# Prompt 14: Streamlit UI

Pattern mix: ABCDE + Audience Persona + Constraint-Satisfaction + PB10

```text
Action:
Implement the Streamlit UI after the graph interface is stable.

Background:
The UI is for a portfolio demo of Quorum. It should show real-time agent progress, generated SQL, critic votes, final report, caveats, and JSON download.

Constraints:
- Entry point is app.py at repo root.
- Use stream_agent / compiled graph streaming behavior, not invoke, for real-time updates.
- Never show Python tracebacks to users.
- Catch exceptions and show st.error.
- SQL must use st.code(sql, language="sql").
- Download button exports InsightReport JSON.
- Do not put workflow logic in the UI.
- Keep UI polished but not bloated.

Details:
Implement:
- app.py
- minimal UI helper functions only if they reduce duplication
- tests or smoke-check guidance as appropriate

Evaluation:
Run available tests.
If feasible, start Streamlit locally and report the URL.
Verify the UI can render mocked or safe states without real provider calls if such a path exists.
```

Stop after this prompt.

---

# Prompt 15: README And Portfolio Notes

Pattern mix: Audience Persona + Template + Fact Checklist

```text
Action:
Create or update README.md for the completed Quorum project.

Background:
The README is for a technical portfolio audience. It should explain architecture, setup, model roles, ensemble critique, limitations, and demo usage.

Constraints:
- Include the sections required by quorum_workflow_design.md.
- Include the Mermaid architecture diagram.
- Include DeepSeek via Anthropic-format note.
- Include data sovereignty note for DeepSeek.
- Include honest limitation that multi-model critique does not eliminate correlated LLM failure.
- Include Gemini preview stability note if the preview model remains in use.
- Do not reveal secrets or local credentials.

Details:
Update:
- README.md

Evaluation:
Check README for completeness against the spec and build_conclusions.md.
```

Stop after this prompt.

---

# Prompt 16: Final Verification And Bloat Audit

Pattern mix: PB10 + Chain-of-Verification + Reflection-Based Reasoning

```text
Action:
Run final verification and perform a bloat audit. Patch only issues found by verification.

Background:
The implementation should now be complete. This phase is for correctness, constraint adherence, and lean-code review.

Constraints:
- Do not add new features.
- Do not refactor broadly unless needed to fix a verified issue.
- Do not make real provider calls unless explicitly performing a live smoke test with user approval and credentials present.

Details:
Verify:
- pytest tests/ -v passes
- no .env is tracked or created for commit
- no DeepSeek SDK dependency exists
- executor has no LLM calls
- tests do not call real LLMs or Snowflake
- prompt files are external
- SQL validator is used by SQL generator
- Snowflake client has no import-time connection
- graph routes match the spec
- empty-results behavior is deterministic
- README notes provider/data risks honestly

Bloat audit:
- identify unused files, unnecessary abstractions, duplicated helper logic, and speculative code
- remove only clearly unnecessary code

Evaluation:
Report final test results, changed files, remaining risks, and any live-smoke-test instructions.
```

---

# Debug Prompt For Any Failed Phase

Pattern mix: PC1 + ReAct/ART + Constraint-Satisfaction

```text
Action:
Debug the current failed phase narrowly. Do not move to the next phase.

Background:
The last phase failed tests or produced an implementation issue. Fix only the current failure.

Constraints:
- Inspect the failing test output first.
- Identify the smallest likely cause.
- Patch only files relevant to the failure.
- Do not rewrite working modules.
- Do not broaden scope.
- Re-run the failing test first, then the phase test set.

Details:
Report:
- failing test or symptom
- root cause
- files changed
- tests re-run
- result

Evaluation:
The debug is complete only when the failing phase passes or a concrete blocker is identified.
```

---

# Compact One-Line Phase Wrapper

Use this when you want a shorter prompt after the agent already knows the chain.

```text
Implement Phase [N] from codex_build_prompt_chain.md only. Follow AGENTS.md, quorum_workflow_design.md, and build_conclusions.md. Keep code lean, satisfy all constraints, add focused tests, run relevant pytest commands, do not start the next phase, and report changed files, test results, and risks.
```

