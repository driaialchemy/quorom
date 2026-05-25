# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Quorum** is an agentic data analyst that converts natural language questions into validated Snowflake SQL queries and generates structured insight reports. It demonstrates LangGraph orchestration, multi-model ensemble critique, and schema-first agent architecture.

**Stack:**
- LangGraph state graph with conditional routing and parallel fan-out
- Snowflake TPCH_SF1 sample dataset
- Pydantic v2 for all contracts (zero raw dicts at node boundaries)
- Multi-model ensemble: Claude Sonnet 4.6 (planner/SQL), GPT-5.5 (Critic A), Gemini 3.1 Pro (Critic B), DeepSeek V4 Pro (Critic C), Claude Opus 4.6 (Arbiter)
- Streamlit UI with real-time graph execution streaming

## Development Commands

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_schemas.py -v

# Run tests for a specific component
pytest tests/test_prompts.py -v
pytest tests/test_schemas.py tests/test_llm_utils.py -v
```

### Running the Application
```bash
# Start Streamlit UI
streamlit run app.py
```

### Environment Setup
```bash
# Install dependencies
pip install -e .

# Or with uv
uv pip install -e .
```

## Architecture Principles

### 1. Schema-First Development
All data contracts are Pydantic v2 models defined in `quorum/schemas/`. Every node boundary is strictly typed. The AgentState in `quorum/state.py` is the single source of truth for graph execution state.

**Critical Rule:** Never use raw dicts at node boundaries. LangGraph update dictionaries are allowed as framework envelopes, but values inside must be typed Pydantic models, primitives, or typed lists.

### 2. LangGraph State Machine
The workflow is orchestrated by LangGraph with:
- **Sequential nodes:** Planner → SQL Generator → Executor
- **Parallel fan-out:** Three independent critic nodes after execution
- **Meta-reasoning:** Arbiter receives all three critiques and makes final decision
- **Conditional routing:** Retry loops on rejection, step advancement on approval
- **Streaming:** UI consumes node updates via `compiled_graph.stream()`

Node signature: `def node_name(state: AgentState) -> dict` returning only modified fields.

### 3. Multi-Model Ensemble Critique
Three independent critics from different providers review each SQL execution result:
- **Critic A (GPT-5.5):** OpenAI, always with `reasoning_effort="high"`
- **Critic B (Gemini 3.1 Pro Preview):** Google
- **Critic C (DeepSeek V4 Pro):** Called via Anthropic SDK format at `https://api.deepseek.com/anthropic`

Claude Opus 4.6 acts as Arbiter, performing meta-analysis of disagreement. The ensemble improves review diversity but does not guarantee correctness (acknowledge this limitation in documentation).

### 4. Deterministic Safety Layers
**SQL Validation (`quorum/tools/sql_validator.py`):**
- Append `LIMIT 50` if missing
- Cap any `LIMIT` above 100
- Reject fully qualified table names (e.g., `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS`)
- Detect and block multi-statement SQL

**Critic Pre-Checks (before LLM calls):**
- Auto-reject if `query_result.success == False`
- Auto-reject if `query_result.row_count == 0`
- Auto-reject if any column is 100% NULL
- Flag warning if `row_count >= 95` (possible truncation)

**Snowflake Executor:**
- Never raises exceptions
- All errors return `QueryResult(success=False, error_detail=...)`
- No LLM calls in executor (purely deterministic)

### 5. Lazy Resource Initialization
- Snowflake connection: initialized on first query, not at module import
- Prompts: loaded at runtime from `prompts/*.txt` files
- Environment variables: validated at startup with clear error messages listing missing vars

## Critical Build Rules

### Absolute Constraints
1. **Never commit `.env`** — only `.env.example` with blank values
2. **Never use raw dicts at node boundaries** — all state updates must be typed
3. **Never raise exceptions in Executor** — return `QueryResult(success=False)` instead
4. **Never call LLMs in Executor** — it is purely deterministic
5. **Always include `LIMIT` in SQL** — append `LIMIT 50` if LLM omits it
6. **Always use unqualified table names** — session is scoped to `TPCH_SF1`
7. **DeepSeek via Anthropic SDK only** — no separate DeepSeek SDK dependency
8. **Model strings must match exactly** — see Model Registry below

### Model Registry (DO NOT SUBSTITUTE)
| Role | Model String | Client | Notes |
|------|--------------|--------|-------|
| Planner | `claude-sonnet-4-6` | `claude_client` | |
| SQL Generator | `claude-sonnet-4-6` | `claude_client` | |
| Critic A | `gpt-5.5-2026-04-23` | `openai_client` | Always `reasoning_effort="high"` |
| Critic B | `gemini-3.1-pro-preview` | `gemini_client` | Async via `client.aio.models.generate_content()` |
| Critic C | `deepseek-v4-pro` | `deepseek_client` | Via Anthropic SDK, enable thinking mode |
| Arbiter | `claude-opus-4-6` | `claude_client` | Separate Opus config |
| Synthesizer | `claude-sonnet-4-6` | `claude_client` | |

### LLM Client Architecture
All three clients in `quorum/llm/` expose identical async interface:
```python
async def call_llm(
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
    model_string: str
) -> BaseModel
```

**Anthropic Client (`anthropic_client.py`):**
- Instantiated twice: once for Claude (standard endpoint), once for DeepSeek (custom base_url)
- DeepSeek config: `thinking={"type": "enabled"}` (omit `budget_tokens`, ignored by DeepSeek)
- Pass `model="deepseek-v4-pro"` explicitly, never rely on default

**Shared Utilities (`llm/utils.py`):**
- `strip_json_fences()` — remove markdown code fences
- `parse_response_model()` — Pydantic validation with retry
- Exceptions: `LLMParseError`, `RateLimitError`

## Repository Structure

```
quorum/
├── state.py              # AgentState (single source of truth)
├── graph.py              # LangGraph assembly (build last)
├── schemas/              # Pydantic models (build first)
│   ├── plan.py           # QueryStep, QueryPlan
│   ├── query.py          # ValidatedQuery, QueryResult
│   ├── critique.py       # CritiqueResult, ArbitrationResult
│   └── report.py         # InsightReport
├── nodes/                # One file per node
│   ├── planner.py
│   ├── sql_generator.py
│   ├── executor.py
│   ├── critic_openai.py
│   ├── critic_gemini.py
│   ├── critic_deepseek.py
│   ├── arbiter.py
│   ├── step_router.py
│   └── synthesizer.py
├── llm/                  # LLM client wrappers
│   ├── utils.py          # Shared parsing/retry logic
│   ├── anthropic_client.py
│   ├── openai_client.py
│   └── gemini_client.py
└── tools/                # Deterministic utilities
    ├── sql_validator.py  # SQL safety checks
    └── snowflake_client.py
prompts/                  # Runtime-loaded .txt files
tests/                    # pytest suite
app.py                    # Streamlit UI (build last)
```

## Build Order (Follow Strictly)

1. **Schemas** → `quorum/schemas/` + `tests/test_schemas.py`
2. **LLM Utils** → `quorum/llm/utils.py` + tests
3. **LLM Clients** → All three provider clients + tests
4. **Prompts** → `.txt` files + `tests/test_prompts.py`
5. **SQL Validator** → `tools/sql_validator.py` + tests
6. **Snowflake Client** → `tools/snowflake_client.py` + mocked tests
7. **Nodes** → One at a time, in graph order, with isolated tests
8. **Graph** → Wire nodes after all pass tests
9. **Streamlit UI** → After `run_agent()` and `stream_agent()` work
10. **Full Verification** → Complete test suite, then live smoke test

**Do not skip ahead.** Each layer must pass tests before proceeding.

## Key Pydantic Conventions

- Use Pydantic v2: `from pydantic import BaseModel, Field, field_validator`
- All `| None` fields default to `None` — never leave optional fields undefaulted
- All `list` fields default to `Field(default_factory=list)`
- `CritiqueResult.confidence_score` validated in range `0.0–1.0`
- `ArbitrationResult.avg_confidence` calculated in Python (not by LLM)
- `InsightReport.generated_at` auto-populates with `datetime.now(timezone.utc)`

## Snowflake TPCH Notes

**Dataset:** `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1`

**Revenue Formula:** `L_EXTENDEDPRICE * (1 - L_DISCOUNT)` (never use `L_TAX` unless explicitly requested)

**Key Tables:**
- `CUSTOMER`, `ORDERS`, `LINEITEM` (core transactional)
- `PART`, `PARTSUPP`, `SUPPLIER` (product/supply chain)
- `NATION`, `REGION` (geographic)

**Connection:**
- Lazy initialization (first query triggers connection)
- Reuse connection across queries
- All errors caught, never raised

## Prompt Conventions

Prompts live in `prompts/*.txt` and are loaded at runtime (not hardcoded in Python).

**Every prompt must end with:**
> "Output strictly valid JSON matching the [SchemaName] schema. No preamble. No markdown fences."

**Dynamic Injection Points:**
- Planner: full TPCH schema context
- SQL Generator: schema context, step objective, `critic_feedback` (on retry)
- Critics: step objective, SQL executed, sample rows, column names
- Arbiter: all three `CritiqueResult` objects, attempt count
- Synthesizer: original question, all approved results

## Graph Routing Logic

**`route_after_arbiter(state)`:**
- If `attempts >= max_attempts` → `"synthesizer"` (graceful exit)
- Elif `arbitration.final_approved` → `"step_router"` (advance step)
- Else → `"sql_generator"` (retry)

**`route_after_step_router(state)`:**
- If `current_step_index >= query_plan.total_steps` → `"synthesizer"` (done)
- Else → `"sql_generator"` (next step)

**Empty Results Behavior:**
- If `all_results` is empty after max retries, do NOT synthesize a fictional report
- Return `InsightReport` with failure-oriented summary, empty findings, `status="failed"`

## Testing Requirements

### Mandatory Test Coverage
- **Schemas:** Validation, defaults, required fields, value ranges
- **Prompts:** File existence, JSON instruction suffix, non-empty
- **LLM Utils:** JSON fence stripping, retry logic, error handling
- **SQL Validator:** LIMIT enforcement, multi-statement rejection, qualified name blocking
- **Nodes:** Isolated tests with mocked clients
- **Graph:** Routing paths, retry loops, step advancement, max retries

### Mocking Strategy
- All LLM clients mocked in `conftest.py` (no real API calls)
- Snowflake connector mocked (no real database calls)
- Critic pre-checks tested without LLM calls

## Environment Variables

Loaded via `python-dotenv`. Fail fast at startup with list of missing variables.

**Required:**
```
ANTHROPIC_API_KEY
OPENAI_API_KEY
GOOGLE_API_KEY
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
SNOWFLAKE_ACCOUNT
SNOWFLAKE_USER
SNOWFLAKE_PASSWORD
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SNOWFLAKE_SAMPLE_DATA
SNOWFLAKE_SCHEMA=TPCH_SF1
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

## Streamlit UI Guidelines

- Entry point: `app.py` in repo root
- Use `compiled_graph.stream()` for real-time updates (not `.invoke()`)
- Never show Python tracebacks — catch exceptions and use `st.error()`
- SQL code blocks: `st.code(sql, language="sql")`
- Download button exports `InsightReport` as JSON
- Display ensemble critique details in expandable sections

## Documentation Honesty Requirements

When updating README or documentation:
- Acknowledge ensemble critique does NOT guarantee correctness
- Note DeepSeek data sovereignty (Chinese company, appropriate for portfolio/demo)
- Flag Gemini 3.1 Pro Preview stability risk
- Include TPCH as sample data disclaimer
- Document LIMIT clauses may exclude long-tail results

## When Debugging

1. Check `quorum_workflow_design.md` for full field-level spec
2. Check `quorum/state.py` for canonical field names
3. Check `prompts/*.txt` for exact prompt text
4. Run `pytest tests/ -v` to identify broken layers
5. Check `build_conclusions.md` for architectural decisions
6. Verify model strings match registry exactly
7. Confirm DeepSeek uses Anthropic SDK format with correct base_url
