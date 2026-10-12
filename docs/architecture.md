# ATLAS System Architecture

ATLAS (**Agentic Tabular Intelligence**) separates the intelligence layer from the computation layer.

```
+-------------------------------------------------------------+
| 01. INTERACTION LAYER (Streamlit + Plotly)                  |
| - Dataset upload & versioning                               |
| - Interactive chat workspace & schema explorer              |
| - Dynamic charts, tables, and execution trace viewer        |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| 02. API & AGENT ORCHESTRATION (FastAPI + Pydantic)          |
| - Finite state machine (Plan -> Validate -> Execute -> Env) |
| - Structured planning & provider adapter                    |
| - Execution budgets & bounded retry loops                   |
+-------------------------------------------------------------+
             |                                     |
             v                                     v
+-----------------------------+     +-------------------------------+
| 03A. ANALYTICS ENGINE       |     | 03B. DOMAIN MEMORY SERVICE    |
| - DuckDB in-memory OLAP     |     | - Scoped metric definitions   |
| - Pandas / NumPy            |     | - Business rules & filters    |
| - SciPy & statsmodels       |     | - Versioning & superseding    |
| - scikit-learn models       |     | - Cross-session persistence   |
+-----------------------------+     +-------------------------------+
             |                                     |
             +------------------+------------------+
                                |
                                v
+-------------------------------------------------------------+
| 04. VERIFICATION & EVIDENCE LEDGER                          |
| - Typed execution envelopes (operation_id, duration_ms)     |
| - Parameter hashing and provenance validation               |
| - Zero hallucinated numerical claims                        |
+-------------------------------------------------------------+
```

## Security Model
- **No Arbitrary Code Execution:** The LLM does not execute arbitrary model-generated Python or unconstrained SQL. All computations flow through registered typed tools.
- **Bounded Queries:** Queries have enforced row limits (`MAX_RESULT_ROWS=500`) and timeout limits (`TOOL_TIMEOUT_SECONDS=30`).
- **Prompt Injection Defense:** Dataset cell contents are strictly treated as data rows, never evaluated as system prompts.
