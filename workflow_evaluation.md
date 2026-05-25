# Quorum Workflow Evaluation

## Executive Verdict

The proposed workflow is a strong way to build Quorum. The macro build path is right: define typed contracts first, isolate provider clients and deterministic tools, build nodes in graph order, wire LangGraph near the end, and build the Streamlit UI last.

I would keep that direction, with a few adjustments before implementation. The highest-value changes are to clarify the LangGraph "dict return" versus "no raw dict boundaries" rule, reduce import-time side effects around Snowflake, centralize LLM JSON parsing and retry behavior, and run focused tests continuously instead of waiting until the end for most test coverage.

In short: the path is mostly correct, but it needs a slightly more defensive implementation sequence to avoid late integration surprises.

## What The Workflow Gets Right

### 1. Schema-first is the correct foundation

Starting with `quorum/schemas/` and `AgentState` is the best choice for this project. The entire system depends on clean contracts between planner, SQL generator, executor, critics, arbiter, and synthesizer.

This matters because the project has many moving parts: multiple LLM providers, Snowflake execution, retries, arbitration, graph routing, and UI streaming. If schemas are ambiguous, every later layer becomes harder to test.

Recommended: keep schemas as the first real implementation phase.

### 2. Graph assembly should happen late

The instruction to touch `graph.py` late is sound. LangGraph wiring is much easier once each node can be tested in isolation with a known input state and a known output update.

Recommended: implement and test node behavior first, then wire the graph after the contracts are stable.

### 3. The deterministic executor boundary is excellent

Keeping the executor purely deterministic is one of the strongest design decisions in the spec.

Executor should:

- Never call an LLM.
- Never raise Snowflake query errors into the graph.
- Always return a `QueryResult`.
- Preserve failed SQL as structured data for critic pre-checks.

This keeps operational failures reviewable by the same workflow that handles semantic failures.

### 4. External prompt files are the right choice

Keeping prompts in `prompts/*.txt` rather than hardcoding them in Python is correct. It makes prompt review, testing, and iteration much cleaner.

Recommended: add tests that verify each prompt file exists and ends with the required JSON-only instruction.

### 5. The ensemble critic pattern is portfolio-worthy

The three-critic plus arbiter design is more compelling than a single LLM judge. It gives the project a clear architectural point of view: one model generates, diverse models critique, and a separate arbiter synthesizes disagreement.

The `disagreement_analysis` requirement is especially good because it forces the system to explain uncertainty rather than just count votes.

## Main Gaps And Risks

### 1. Clarify "no raw dicts" at LangGraph boundaries

There is a tension in the spec:

- Absolute rule: never use raw dicts at node boundaries.
- LangGraph convention: each node returns `dict` updates.

That is not fatal, but it must be defined clearly before build.

Recommended interpretation:

LangGraph update dictionaries are allowed only as the framework transport envelope. The values inside those updates must be Pydantic models, primitives, or lists of Pydantic models. No untyped business payloads should move between nodes.

Example acceptable return:

```python
return {"query_plan": query_plan}
```

Example to avoid:

```python
return {"query_plan": {"steps": [...], "reasoning": "..."}}
```

This keeps the spirit of the rule while respecting LangGraph's API.

### 2. Snowflake import-time connection may hurt tests

The design says the Snowflake connection is initialized once at module load. That is efficient in production, but it can make tests and local imports brittle.

Risk:

- Importing `quorum.tools.snowflake_client` may fail before mocks can be applied.
- Missing `.env` values could break unit tests that do not need Snowflake.
- Streamlit startup could fail before rendering a useful error.

Recommended adjustment:

Use a lazy singleton connection. Load environment at startup, validate required variables in a dedicated config function, and create the Snowflake connection on first query or explicit initialization. Still reuse the connection after creation.

This preserves the "do not create a new connection per query" rule without making import itself dangerous.

### 3. Testing should be continuous, not mostly last

The build order says complete tests come last, and it correctly calls out `test_schemas.py` early. For this project, waiting too long to test nodes and clients would create unnecessary integration risk.

Recommended adjustment:

Keep the official build order, but run focused tests after each layer:

- After schemas: `pytest tests/test_schemas.py -v`
- After LLM clients: parser and retry tests with mocked SDK responses
- After Snowflake client: mocked success and failure tests
- After each node: isolated node tests
- After graph assembly: routing and retry path tests
- After UI: smoke test Streamlit rendering manually or with a lightweight harness

The final complete test suite can still be finished after the app.

### 4. Centralize LLM parsing and retry behavior

All three LLM clients share the same contract:

- Call provider.
- Extract response text.
- Strip JSON fences.
- Validate with Pydantic.
- Retry once on parse failure.
- Raise a shared parse error on second failure.

If each client implements that independently, the code will drift.

Recommended adjustment:

Create shared helpers in `quorum/llm/base.py` or `quorum/llm/utils.py`:

- `strip_json_fences(text: str) -> str`
- `parse_response_model(text: str, response_model: type[BaseModel]) -> BaseModel`
- `build_retry_prompt(...) -> str`
- shared exceptions like `LLMParseError` and `RateLimitError`

Provider clients should only handle provider-specific request and response extraction.

### 5. The critic fan-out strategy should be chosen pragmatically

The preferred LangGraph Send API fan-out is architecturally attractive and demonstrates LangGraph well. However, it is also one of the more complex parts of the system.

Recommended path:

Build the critic logic so it is independent of graph topology. Then choose one of these:

- If portfolio demonstration of LangGraph parallelism is a priority, implement Send API fan-out.
- If fastest reliable v1 is the priority, start with a single `ensemble_critic` node using `asyncio.gather()`, then refactor to Send API after the full workflow is green.

The current spec already allows this fallback. The important part is to avoid coupling critic business logic to the first graph implementation.

### 6. SQL safety needs a deterministic post-processor

The spec says generated SQL must always include `LIMIT`, must cap at 100 rows, and must use unqualified table names. Relying only on the prompt is not enough.

Recommended adjustment:

Add deterministic SQL validation/post-processing after the SQL generator LLM returns:

- Append `LIMIT 50` if missing.
- Reject or rewrite limits above 100.
- Detect fully qualified table references like `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS`.
- Detect obvious multi-statement SQL.
- Optionally allow only `SELECT` statements for v1.

This can live as a small helper used by `nodes/sql_generator.py`.

### 7. Max retry behavior needs careful partial-result handling

The graph says max retries route to synthesizer. That is reasonable, but the synthesizer must handle cases where `all_results` is empty or the current step failed repeatedly.

Recommended adjustment:

Define explicit behavior:

- If no approved results exist, return a failed or partial `InsightReport` with strong caveats.
- If prior steps succeeded but the current step failed, synthesize from prior approved results only.
- Include the failed step and retry count in caveats.

Without this, the synthesizer may be asked to write a business report from no usable data.

## Recommended Build Path

This is the best practical sequence I would use:

### Phase 0: Repository and config hygiene

Create the project skeleton, `.gitignore`, `.env.example`, `pyproject.toml`, and package directories. Add config loading and missing-variable validation early, but avoid importing live provider clients during unit tests.

### Phase 1: Schemas and state

Implement:

- `quorum/state.py`
- `quorum/schemas/plan.py`
- `quorum/schemas/query.py`
- `quorum/schemas/critique.py`
- `quorum/schemas/report.py`
- `tests/test_schemas.py`

Use `Field(default_factory=list)` for list defaults unless the project specifically requires literal `[]`. This still defaults to an empty list but avoids mutable-default ambiguity.

Consider using `datetime.now(timezone.utc)` for `InsightReport.generated_at` instead of naive `datetime.utcnow()` if timezone-aware timestamps are acceptable.

### Phase 2: Prompt files and LLM foundation

Create all prompt files before node implementation. Then build shared LLM utilities and provider clients.

Implement the shared `call_llm` interface for:

- Anthropic and DeepSeek through `anthropic_client.py`
- OpenAI through `openai_client.py`
- Gemini through `gemini_client.py`

Add mocked tests for JSON parsing, fence stripping, parse retry, and provider-specific model parameter selection.

### Phase 3: Snowflake tool

Implement `snowflake_client.py` with:

- Lazy reusable connection
- `execute_query(sql: str) -> QueryResult`
- `get_schema_context() -> str`
- all exceptions converted to `QueryResult(success=False, error_detail=...)` during execution

Mock Snowflake in tests. Do not require real credentials for unit tests.

### Phase 4: Nodes in graph order

Build one node at a time:

1. Planner
2. SQL generator
3. Executor
4. Critic shared pre-check helpers
5. OpenAI critic
6. Gemini critic
7. DeepSeek critic
8. Arbiter
9. Step router
10. Synthesizer

Each node should have isolated tests before graph wiring.

### Phase 5: Graph assembly

Wire `graph.py` only after node tests pass. Start with the simplest topology that satisfies the spec, then add parallel fan-out if not already used.

Required graph tests:

- Happy path
- SQL failure and retry
- Zero-row retry
- Max retries
- Multi-step success
- 2-1 critic split
- Empty approved results

### Phase 6: Streamlit UI

Build `app.py` after `run_agent()` and `stream_agent()` are stable. The UI should not contain workflow logic. It should render graph events, SQL, votes, final report, caveats, and download JSON.

### Phase 7: Final verification

Run:

```bash
pytest tests/ -v
```

Then perform one controlled live Snowflake run only after mocks pass and credentials are present.

## Priority Recommendations

### Must fix before implementation

- Define the LangGraph update dict as a framework envelope, not a business payload.
- Avoid unavoidable Snowflake/provider side effects at import time.
- Centralize LLM JSON parsing and retry logic.
- Add deterministic SQL post-processing for `LIMIT`, row cap, unqualified tables, and single-statement `SELECT`.
- Define synthesizer behavior when no approved results exist.

### Should fix during implementation

- Add per-layer tests instead of deferring most testing to the end.
- Keep critic pre-check logic shared so the three critic nodes do not diverge.
- Make model strings configurable through a registry constant, while preserving the required defaults.
- Add prompt existence and prompt ending tests.
- Add a startup model/config smoke check that can be run manually without affecting unit tests.

### Can defer until after v1

- Full LangGraph Send API fan-out if `asyncio.gather()` is used initially.
- More advanced SQL parsing with a full SQL parser.
- Checkpointing and resumability.
- Rich UI polish beyond clear streaming status and result display.
- Cost telemetry and token accounting.

## Best Path Decision

The documented path is a good way to build Quorum and is close to the best path for a portfolio-grade agentic data analyst. I would not replace it with a radically different architecture.

The best version of the path is:

1. Keep schema-first development.
2. Build provider clients and deterministic tools behind stable interfaces.
3. Test every node in isolation.
4. Wire the graph late.
5. Start with reliability, then add graph sophistication.
6. Build the UI only after the graph stream is stable.

With those adjustments, the workflow should produce a cleaner implementation, faster debugging, and a stronger final demo.
