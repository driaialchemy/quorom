# Quorum Implementation Plan

## Phase 0: Spec Assimilation

Status: complete.

Build from these source documents:

- `AGENTS.md`
- `quorum_workflow_design.md`
- `build_conclusions.md`
- `codex_build_prompt_chain.md`

Decision: proceed with the original Quorum architecture, amended by `build_conclusions.md`.

## Phase 1: Repository Skeleton And Config Hygiene

Files to create:

- `pyproject.toml`
- `.gitignore`
- `.env.example`
- package directories under `quorum/`
- `__init__.py` files for package directories
- empty `prompts/` and `tests/` directories

Tests:

- No focused pytest file is expected in this phase.
- Verify file structure with a lightweight directory listing.

Stopping condition:

- Skeleton exists.
- `.env` is ignored.
- `.env.example` contains required keys with blank values, except documented safe defaults if intentionally retained.
- No schemas, clients, tools, nodes, graph, or UI logic exists yet.

Risks:

- Accidentally implementing future-phase code too early.
- Adding dependencies beyond the approved project spec.
- Creating real credentials or a `.env` file.

## Phase 2: Schemas And AgentState

Files to create or edit:

- `quorum/state.py`
- `quorum/schemas/plan.py`
- `quorum/schemas/query.py`
- `quorum/schemas/critique.py`
- `quorum/schemas/report.py`
- `quorum/schemas/__init__.py`
- `tests/test_schemas.py`

Tests:

- `pytest tests/test_schemas.py -v`

Stopping condition:

- All schema tests pass.
- Pydantic defaults and validators match the spec.
- No non-schema implementation has started.

Risks:

- Mutable list defaults if implemented carelessly.
- Optional fields missing explicit defaults.
- Raw dict stand-ins replacing real schema models.

## Phase 3: Prompt Files And Prompt Tests

Files to create:

- `prompts/planner.txt`
- `prompts/sql_generator.txt`
- `prompts/critic.txt`
- `prompts/arbiter.txt`
- `prompts/synthesizer.txt`
- `tests/test_prompts.py`

Tests:

- `pytest tests/test_prompts.py -v`

Stopping condition:

- Prompt files exist.
- Each prompt ends with the required JSON-only instruction.
- No prompt text is hardcoded in Python nodes.

Risks:

- Prompt/schema name mismatch.
- Runtime file loading failures hidden until graph execution.

## Phase 4: Shared LLM Utilities

Files to create:

- `quorum/llm/utils.py`
- `tests/test_llm_utils.py`

Tests:

- `pytest tests/test_llm_utils.py -v`
- `pytest tests/test_schemas.py tests/test_llm_utils.py -v`

Stopping condition:

- JSON fence stripping, Pydantic parsing, retry prompt construction, and shared exceptions are tested.
- Provider clients are not implemented yet.

Risks:

- Duplicating parsing logic later in provider clients.
- Making utilities provider-specific too early.

## Phase 5: LLM Provider Clients

Files to create:

- `quorum/llm/anthropic_client.py`
- `quorum/llm/openai_client.py`
- `quorum/llm/gemini_client.py`
- provider client tests

Tests:

- Run focused mocked LLM client tests.
- No real provider calls.

Stopping condition:

- All clients expose the shared async `call_llm` interface.
- DeepSeek uses Anthropic SDK format.
- No DeepSeek SDK is added.

Risks:

- SDK API uncertainty.
- Hidden real API calls in tests.

## Phase 6: SQL Validator

Files to create:

- `quorum/tools/sql_validator.py`
- `tests/test_sql_validator.py`

Tests:

- `pytest tests/test_sql_validator.py -v`

Stopping condition:

- Missing limits are appended.
- Limits above 100 are capped.
- Fully qualified TPCH table names are rejected.
- Obvious multi-statement SQL is rejected.

Risks:

- Overbuilding a SQL parser.
- Underblocking unsafe SQL.

## Phase 7: Snowflake Client

Files to create:

- `quorum/tools/snowflake_client.py`
- `tests/test_snowflake_client.py`

Tests:

- `pytest tests/test_snowflake_client.py -v`

Stopping condition:

- Lazy reusable connection behavior is implemented.
- `execute_query` returns `QueryResult` on execution failure.
- Tests mock Snowflake.

Risks:

- Import-time connection side effects.
- Unit tests requiring real credentials.

## Phase 8: Nodes

Files to create:

- one node module per spec under `quorum/nodes/`
- focused node tests

Tests:

- Run focused tests after each node or node group.

Stopping condition:

- Each node is tested in isolation before graph wiring.
- LangGraph update dictionaries contain typed values, not raw business dicts.

Risks:

- Implementing graph routing before node behavior is stable.
- Repeating critic pre-check logic instead of sharing it.

## Phase 9: Graph Assembly

Files to create:

- `quorum/graph.py`
- `tests/test_graph.py`

Tests:

- `pytest tests/test_graph.py -v`
- `pytest tests/ -v`

Stopping condition:

- Routing paths pass.
- Retry and max-retry behavior pass.
- Empty-results behavior is deterministic.

Risks:

- Fan-out complexity obscuring basic correctness.
- Missing route coverage.

## Phase 10: Streamlit UI

Files to create:

- `app.py`

Tests:

- Full test suite.
- Manual or local smoke test if feasible.

Stopping condition:

- UI uses streaming graph events.
- UI catches exceptions without exposing tracebacks.
- No workflow logic is embedded in UI code.

Risks:

- UI coupling to internal graph details.
- Attempting real provider calls during basic UI checks.

## Phase 11: README And Final Verification

Files to create or edit:

- `README.md`

Tests:

- `pytest tests/ -v`

Stopping condition:

- README contains required architecture, setup, limitations, DeepSeek data sovereignty note, and ensemble caveat.
- Bloat audit finds no speculative code.

Risks:

- Overselling ensemble correctness.
- Omitting provider and data risks.
