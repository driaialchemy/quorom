# Quorum Build Conclusions

## Final Verdict

Quorum should be built using the current workflow, but with several pre-build amendments. The original architecture is strong enough to proceed: schema-first development, deterministic Snowflake execution, external prompt files, multi-model critique, and late LangGraph assembly are all sound choices for a portfolio-grade agentic data analyst.

The build should not be treated as fully validated, though. The follow-up critique correctly identifies that the earlier workflow evaluation was more implementation checklist than strategic stress test. The final path should preserve the original structure while making the reliability, testing, empty-result, and SQL-safety decisions explicit before coding begins.

The practical conclusion: proceed with the build, but make a short spec revision first.

## What To Keep

### Keep the schema-first build order

Start with `AgentState` and all Pydantic models. This remains the correct foundation because every node, test, graph route, and UI rendering path depends on these contracts.

### Keep LangGraph

LangGraph is justified for this project. A simpler Python loop would be easier, but it would weaken the portfolio signal. The point of Quorum is not only to answer Snowflake questions; it is to demonstrate a typed, inspectable, multi-node agent workflow with retries, fan-out, arbitration, and streaming.

Use LangGraph intentionally, but do not over-optimize the graph topology too early.

### Keep the ensemble critic pattern

The ensemble critic design is worth keeping because it is the project's main differentiator. It gives the app a clear story: one model plans and writes SQL, independent models critique the result, and a separate arbiter explains disagreement.

However, it should be presented honestly. The ensemble does not eliminate correlated model failure. The README should explicitly say that multiple LLM critics improve diversity of review, but they do not guarantee correctness.

### Keep Snowflake TPCH for v1

TPCH is acceptable for v1 because it is available, stable, and familiar. Its weakness is demo aesthetics: customer and part names are not especially compelling for non-technical audiences.

Do not block v1 on finding a richer dataset. Instead, make the UI and example questions emphasize business metrics, ranks, trends, and revenue calculations rather than raw entity names.

## Required Spec Changes Before Build

### 1. Add shared LLM utilities

Add `quorum/llm/utils.py`.

It should own:

- `strip_json_fences(text: str) -> str`
- `parse_response_model(text: str, response_model: type[BaseModel]) -> BaseModel`
- retry prompt construction
- `LLMParseError`
- `RateLimitError`

The provider clients should handle provider-specific API calls only. JSON cleanup, Pydantic validation, and retry behavior should not be reimplemented three times.

### 2. Use lazy Snowflake connection initialization

Do not connect to Snowflake at module import time.

Use a lazy singleton:

- Importing `snowflake_client.py` should not require credentials.
- Unit tests should be able to mock execution without a live connection.
- The first real query, or an explicit startup check, should create the connection.
- The connection should still be reused after creation.

This preserves the "do not create a new connection per query" rule while keeping tests and local imports sane.

### 3. Add deterministic SQL validation

Prompt instructions are not enough. Add a deterministic SQL validator/post-processor, preferably in `quorum/tools/sql_validator.py`.

Minimum v1 behavior:

- Require a single `SELECT` statement.
- Reject obvious multi-statement SQL.
- Append `LIMIT 50` if missing.
- Cap any `LIMIT` above 100.
- Detect and reject fully qualified table names like `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS`.
- Preserve unqualified TPCH table names.

This should run immediately after the SQL Generator LLM returns and before the Executor node receives SQL.

### 4. Define empty-results behavior

If max retries are exhausted and `all_results` is empty, do not call the Synthesizer LLM to invent a business report from nothing.

Instead:

- Return an `InsightReport` with a failure-oriented executive summary.
- Set `key_findings=[]`.
- Set `data_tables=[]`.
- Include caveats explaining that no query result was approved within the retry limit.
- Set graph `status="failed"`.

If earlier steps succeeded but a later step failed, synthesize only from approved prior results and include a caveat about the failed step.

### 5. Make per-layer testing mandatory

Testing cannot wait until the end. The final test suite can be completed last, but focused tests must be written and run as each layer is built.

Required sequence:

1. Schema tests after schemas.
2. LLM parsing/retry tests after LLM utilities.
3. SQL validator tests before SQL generator node tests.
4. Snowflake client tests with mocked connector.
5. Isolated node tests before graph wiring.
6. Graph routing tests before Streamlit.
7. Streamlit smoke test after UI.

This is not optional hygiene; it is the main protection against opaque graph-level failures.

### 6. Add prompt tests

Add `tests/test_prompts.py`.

It should verify:

- Every required prompt file exists.
- Every prompt ends with the required JSON-only instruction.
- No prompt is empty.

Prompt files are runtime dependencies, so they deserve basic tests.

## Decisions On Debated Points

### LangGraph update dictionaries

This is a documentation clarification, not a serious architecture risk.

Final rule: LangGraph node return dictionaries are allowed as framework update envelopes. The values inside those dictionaries must be typed Pydantic models, primitives, or typed lists. No raw business dictionaries should cross node boundaries.

Add one line to `AGENTS.md` or the implementation notes, then move on.

### Fan-out implementation

For v1, implement the simplest reliable graph topology that passes tests.

Preferred path:

1. Build each critic as an independent node function with shared pre-check helpers.
2. If LangGraph Send API is straightforward, use it.
3. If it slows the build, use one `ensemble_critic` node with `asyncio.gather()`.

The important portfolio behavior is parallel independent critique and arbiter reasoning. The exact fan-out mechanism is less important than correctness and debuggability.

### Gemini preview risk

Keep `gemini-3.1-pro-preview` because the project spec requires it, but isolate model strings in a central registry.

If the preview model becomes unavailable or unstable during build, substitute the nearest stable Gemini 3.x Pro model only after documenting the deviation.

### DeepSeek data sovereignty

Keep DeepSeek for the portfolio demo, but the README must include a clear data sovereignty note. Do not imply that this exact model mix is automatically appropriate for client or production data.

### Claude Opus as arbiter

Keep Claude Opus as arbiter for v1. It fits the original design and separates generation/critique/arbitration roles clearly.

Do not spend v1 time benchmarking GPT-5.5 versus Claude Opus as arbiter unless the first implementation shows arbiter quality problems.

### Datetime and list defaults

Use normal modern Pydantic/Python practice, but do not let these become architectural distractions.

Recommended implementation:

- `Field(default_factory=list)` for list fields.
- `datetime.now(timezone.utc)` if timezone-aware serialization causes no friction.

These are craftsmanship details, not build blockers.

## Final Build Plan

### Phase 0: Amend the spec

Before writing the application code, update the plan to include:

- `quorum/llm/utils.py`
- `quorum/tools/sql_validator.py`
- lazy Snowflake connection behavior
- explicit empty-results behavior
- mandatory per-layer tests
- README notes on correlated LLM failure, DeepSeek data sovereignty, and Gemini preview risk

### Phase 1: Build contracts

Implement schemas, `AgentState`, and schema tests.

### Phase 2: Build shared infrastructure

Implement config loading, LLM utilities, provider clients, prompt loading, prompt tests, SQL validator, and Snowflake client with mocks.

### Phase 3: Build nodes

Implement nodes in graph order. Keep critic pre-check logic shared. Test each node in isolation.

### Phase 4: Wire graph

Wire LangGraph only after nodes pass. Start with the most reliable topology. Add or preserve fan-out only if it remains clean under test.

### Phase 5: Build Streamlit UI

Build UI after `run_agent()` and `stream_agent()` work. The UI should render graph events and final reports, not contain workflow logic.

### Phase 6: Verify

Run the full mocked test suite. Then do one controlled live Snowflake smoke test with credentials present.

## Bottom Line

Build Quorum. The architecture is good enough and interesting enough to justify proceeding.

The final build should be slightly more conservative than the original spec:

- More deterministic validation around SQL.
- Less import-time side effect risk.
- More shared client infrastructure.
- More testing before graph integration.
- More honest README language about ensemble limits and provider risk.

That combination gives the project the best chance of becoming both a working app and a credible portfolio piece.
