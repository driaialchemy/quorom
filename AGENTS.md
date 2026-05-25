# AGENTS.md — Quorum

> This file is read by OpenAI Codex before every session. Follow all instructions here exactly.

---

## Project Identity

**Name:** Quorum
**Purpose:** Agentic data analyst — natural language → Snowflake SQL → structured insight report
**Stack:** LangGraph + Snowflake + Pydantic v2 + multi-model ensemble critique
**Python version:** 3.11+
**Package manager:** pip / uv with `pyproject.toml`

---

## Absolute Rules

1. **Never commit `.env`** — credentials live in `.env` only. `.env.example` is safe to commit.
2. **Never use raw dicts at node boundaries** — every node input and output is a Pydantic model.
3. **Never raise exceptions inside the Executor node** — all Snowflake errors return `QueryResult(success=False, error_detail=...)`.
4. **Never call LLMs inside the Executor node** — it is purely deterministic.
5. **Always include `LIMIT` in generated SQL** — maximum 100 rows. Append `LIMIT 50` if the LLM omits it.
6. **Always use unqualified table names in SQL** — write `ORDERS`, not `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS`. The Snowflake session is already scoped.
7. **Never use `deepseek-chat` or `deepseek-reasoner`** — these are deprecated. Always use `deepseek-v4-pro`.
8. **DeepSeek is called via the Anthropic SDK** — base URL `https://api.deepseek.com/anthropic`. Do not install a separate DeepSeek SDK.

---

## Repository Layout

```
quorum/                     ← Python package root
├── state.py                ← AgentState (single source of truth)
├── graph.py                ← LangGraph assembly — touch last
├── schemas/                ← Pydantic schemas — build first
├── nodes/                  ← One file per node
├── llm/                    ← Three LLM client wrappers
└── tools/                  ← Snowflake client (no LLM)
prompts/                    ← .txt prompt files loaded at runtime
tests/                      ← pytest test suite
app.py                      ← Streamlit UI — build last
```

---

## Build Order

Always build in this sequence. Do not skip ahead.

```
1. schemas/          → all Pydantic models + test_schemas.py
2. llm/              → three LLM clients + shared interface
3. tools/            → snowflake_client.py
4. nodes/            → one node per session, in graph order
5. graph.py          → wire nodes, edges, routing functions
6. app.py            → Streamlit UI
7. tests/            → complete test suite
```

---

## LLM Client Architecture

Three clients in `quorum/llm/`. All async. All expose the same interface:

```python
async def call_llm(
    system_prompt: str,
    user_prompt: str,
    response_model: type[BaseModel],
    model_string: str
) -> BaseModel
```

### `anthropic_client.py` — handles TWO providers

```python
# Claude (primary nodes + Arbiter)
claude_client = AnthropicLLMClient(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=None
)

# DeepSeek V4 Pro (Critic C) — via Anthropic SDK format
deepseek_client = AnthropicLLMClient(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL")  # https://api.deepseek.com/anthropic
)
```

When calling DeepSeek:
- Pass `model="deepseek-v4-pro"` explicitly — never rely on default routing
- Enable thinking: `thinking={"type": "enabled"}` — omit `budget_tokens` (ignored by DeepSeek)

### `openai_client.py` — GPT-5.5 only
- Model: `gpt-5.5-2026-04-23`
- Always set `reasoning_effort="high"`

### `gemini_client.py` — Gemini 3.1 Pro Preview only
- Model: `gemini-3.1-pro-preview`
- Async via `client.aio.models.generate_content()`
- System prompt via `types.GenerateContentConfig(system_instruction=...)`

---

## Model Registry

| Role | Model String | Client |
|---|---|---|
| Planner | `claude-sonnet-4-6` | `claude_client` |
| SQL Generator | `claude-sonnet-4-6` | `claude_client` |
| Critic A | `gpt-5.5-2026-04-23` | `openai_client` |
| Critic B | `gemini-3.1-pro-preview` | `gemini_client` |
| Critic C | `deepseek-v4-pro` | `deepseek_client` |
| Arbiter | `claude-opus-4-6` | `claude_client` (Opus config) |
| Synthesizer | `claude-sonnet-4-6` | `claude_client` |

---

## Pydantic Conventions

- Use Pydantic v2 throughout (`from pydantic import BaseModel, field_validator`)
- All `| None` fields default to `None` — never leave optional fields undefaulted
- All `list` fields default to `[]` — never leave list fields undefaulted
- `CritiqueResult.confidence_score` must be validated in range 0.0–1.0
- `ArbitrationResult.avg_confidence` is calculated in Python — never by LLM
- `InsightReport.generated_at` auto-populates as `datetime.utcnow()`

---

## LangGraph Conventions

- State class: `AgentState` in `state.py` — import it everywhere
- Every node signature: `def node_name(state: AgentState) -> dict`
- Nodes return only the fields they modify — never return the full state
- Routing functions are standalone functions, not lambdas
- Fan-out pattern for critics: LangGraph Send API (Option A) preferred. Fall back to `asyncio.gather()` in a single `ensemble_critic` node if Send API causes issues
- Compile graph with `graph.compile()` — no checkpointing in v1
- Expose `run_agent()` and `stream_agent()` as the public interface in `graph.py`

---

## Prompt Conventions

- Prompts are `.txt` files in `prompts/` — never hardcode prompt text in Python files
- Load prompts at module import time, not inside node functions
- Every prompt ends with: "Output strictly valid JSON matching the [SchemaName] schema. No preamble. No markdown fences."
- LLM client strips ` ```json ` fences before Pydantic validation

---

## Environment Variables

Load via `python-dotenv` at startup. Fail fast if any required variable is missing — print a list of all missing variables before exiting.

Required variables:
```
ANTHROPIC_API_KEY
OPENAI_API_KEY
GOOGLE_API_KEY
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
SNOWFLAKE_ACCOUNT
SNOWFLAKE_USER
SNOWFLAKE_PASSWORD
SNOWFLAKE_WAREHOUSE
SNOWFLAKE_DATABASE
SNOWFLAKE_SCHEMA
SNOWFLAKE_ROLE
```

---

## Testing

Run tests with:
```bash
pytest tests/ -v
```

Run a single test file:
```bash
pytest tests/test_schemas.py -v
```

Test conventions:
- Mock all LLM clients in `conftest.py` — no real API calls in tests
- Mock `snowflake_client` — no real Snowflake calls in tests
- Every critic pre-check (zero rows, SQL failure) has a dedicated test
- Every graph routing path has a dedicated test

---

## Snowflake Notes

- Dataset: `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1`
- Revenue formula: `L_EXTENDEDPRICE * (1 - L_DISCOUNT)`
- Never use `L_TAX` in revenue calculations unless explicitly requested
- All executor errors are caught and returned as `QueryResult(success=False, error_detail=...)`
- Connection initialized once at module load — do not create a new connection per query

---

## Streamlit Notes

- Entry point: `app.py` in repo root
- Use `compiled_graph.stream()` for real-time node updates — not `.invoke()`
- Never show Python tracebacks to the user — catch all exceptions and show `st.error()`
- SQL code blocks use `st.code(sql, language="sql")`
- Download button exports `InsightReport` as JSON via `st.download_button()`

---

## When Stuck

1. Check `quorum_workflow_design.md` for full field-level specification
2. Check `quorum/state.py` for the canonical field names
3. Check `prompts/` for the exact prompt each node should use
4. Run `pytest tests/ -v` to identify what is broken before proceeding

---

*Last updated: May 2026*
