# ATLAS — Agentic Tabular Intelligence

> **Ask anything. Analyze everything. Remember what matters.**

ATLAS is a dataset-agnostic agentic data-analysis workspace that turns natural-language questions into reproducible, evidence-backed analytical computations. Upload any CSV or Excel file (or launch the One-Click Retail Demo), ask analytical questions, and watch the agent create a structured plan, execute registered analytical tools, validate its findings, apply persistent cross-session domain memory, and return answers with an inspectable execution trace.

- **Live Deployment (Vercel):** [https://atlas-iota-pied.vercel.app](https://atlas-iota-pied.vercel.app)
- **Core Engineering Principle:** *The LLM plans and interprets; Python and SQL perform the computations. Every numerical claim is grounded in actual tool execution results.*

---

## 🛠️ Distinct Analytical Tool Catalogue (8 Registered Tools)

ATLAS implements **8 genuinely distinct analytical tools** in `atlas/tools/` registered via a typed Pydantic `ToolRegistry` (`atlas/tools/registry.py`). Each tool performs a fundamentally different class of analysis and returns a standardized `ToolExecutionEnvelope` (`operation_id`, `validated_parameters`, `result`, `warnings`, `duration_ms`):

| # | Tool Name | Module | Underlying Engine | Distinct Analytical Purpose & Output |
|---|-----------|--------|-------------------|--------------------------------------|
| 01 | `profile_dataset` | `atlas/tools/profile.py` | Pandas + NumPy | Infers column data types, missingness counts/percentages, cardinality, duplicate row counts, candidate primary keys, temporal columns, numeric percentiles (`p25`, `median`, `p75`, `mean`, `std`), and top category frequencies. |
| 02 | `query_data` | `atlas/tools/query.py` | DuckDB OLAP SQL | Executes bounded, read-only SQL queries with validated `GROUP BY`, multi-metric aggregations (`SUM`, `AVG`, `COUNT`, `MIN`, `MAX`, `COUNT DISTINCT`), structured filters, custom `sql_filter` injection from domain memory, and top-$N$ sorting. |
| 03 | `analyze_relationships` | `atlas/tools/relationships.py` | SciPy (`pearsonr`, `spearmanr`, `chi2_contingency`) | Computes pairwise Pearson linear correlation and Spearman rank correlation matrices with exact $p$-values and sample sizes for numeric pairs, plus Cramér's V association matrices for categorical variables. |
| 04 | `analyze_trends` | `atlas/tools/trends.py` | Pandas Time-Series Resampling | Parses temporal columns, groups by configurable periods (`day`, `week`, `month`, `quarter`, `year`), computes period-over-period absolute and percentage growth rates, rolling window averages, and start-to-end trend trajectories. |
| 05 | `detect_anomalies` | `atlas/tools/anomalies.py` | NumPy Quantiles + `scikit-learn` (`IsolationForest`) | Performs univariate interquartile range ($1.5 \times \text{IQR}$) and Z-score outlier boundary detection as well as multivariate Isolation Forest anomaly scoring, returning anomalous records and decision scores. |
| 06 | `run_statistical_test` | `atlas/tools/statistical.py` | SciPy Stats (`ttest_ind`, `mannwhitneyu`, `f_oneway`, `kruskal`, `levene`) | Runs formal hypothesis tests (Independent $t$-test, Mann–Whitney U, One-Way ANOVA, Kruskal–Wallis, and Chi-Square test of independence) with Levene variance assumption checks and effect sizes (Cohen's $d$, Rank-biserial, Cramér's V). |
| 07 | `build_baseline_model` | `atlas/tools/modeling.py` | `scikit-learn` (`RandomForestClassifier`, `RandomForestRegressor`, `ColumnTransformer`) | Builds an automated ML pipeline with median/mode imputation, standard scaling, one-hot encoding, stratified 80/20 train/test split, held-out evaluation metrics (`accuracy`, `f1_weighted`, `precision`, `recall` or `r2_score`, `mae`, `rmse`), and top feature importances. |
| 08 | `generate_visualization` | `atlas/tools/visualization.py` | Plotly (`plotly.express`, `plotly.graph_objects`) | Validates column existence and builds interactive Plotly specifications for `bar`, `line`, `scatter`, `histogram`, `box`, and correlation `heatmap` charts. |

In addition to the 8 analytical tools, ATLAS implements `retrieve_memory` and `manage_memory` via `MemoryService` (`atlas/memory/service.py`) to persist and apply domain knowledge across sessions.

---

## 🧠 Persistent Cross-Session Domain Memory

Unlike chat-history storage, ATLAS stores structured, versioned domain rules in SQLite/PostgreSQL (`MemoryRecord` in `atlas/persistence/db.py`):
- **Metric Definitions & Business Rules:** e.g. `active_customer_orders` → `order_status != 'Cancelled'`
- **Column Semantics & Units:** Mapping domain columns and units across dataset versions.
- **Versioning & Supersession:** Updating an existing key increments `version`, marks the prior record `superseded`, and links `superseded_by`.
- **Direct Impact on Calculations:** Active memory rules are automatically injected into query plans (`sql_filter`), changing the actual computed totals and recording the applied memory inside the execution trace (`tests/memory/test_memory.py`).

---

## 🏗️ System Architecture

```
atlas/
├── atlas/
│   ├── config.py              # Typed environment settings & execution budgets
│   ├── ingestion/parser.py    # Universal CSV/TSV/XLSX validation & schema discovery
│   ├── analytics/engine.py    # Read-only DuckDB OLAP sandbox & SQL injection guards
│   ├── tools/                 # 8 distinct analytical tools + typed Pydantic registry
│   ├── agent/                 # Finite-state orchestrator & LLM/deterministic adapter
│   ├── memory/service.py      # Scoped cross-session memory CRUD & versioning
│   ├── evidence/ledger.py     # Provenance ledger & standardized execution envelopes
│   └── persistence/db.py      # SQLAlchemy ORM models (Datasets, Memories, Analyses)
├── backend/                   # FastAPI REST API (/api/datasets, /api/analyses, /api/memories)
├── frontend/                  # Streamlit interactive workspace & Dashboard Stage
├── public/                    # Split-screen Web UI & One-Click Retail Demo for Vercel
├── api/                       # Serverless FastAPI entrypoint for Vercel deployment
├── tests/                     # 22 unit, integration, agent, memory, security & evaluation tests
├── examples/                  # Synthetic multi-version data generator & demo scenarios
└── docs/                      # Architecture, tool contracts, memory design & evaluation docs
```

---

## 🚀 Local Setup & Execution

### 1. Install Dependencies
```powershell
git clone https://github.com/sahooarnav2007-gif/Atlas.git
cd Atlas
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Generate Sample Datasets
```powershell
python examples/generate_sample_data.py
```

### 3. Start Backend & Frontend
Terminal 1 (FastAPI Backend + Web UI on port 8000):
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2 (Streamlit Workspace on port 8501):
```powershell
python -m streamlit run frontend/app.py --server.port 8501
```

### 4. Run Automated Tests
```powershell
pytest -v
```
