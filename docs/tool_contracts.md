# Tool Contracts & Catalogue

ATLAS registers 8 distinct analytical tools with strict Pydantic schemas and standardized execution envelopes.

## 1. `profile_dataset`
- **Purpose:** Ingests any tabular data and discovers types, missingness, cardinality, duplicates, candidate keys, and distributions.
- **Input:** `{ columns: Optional[List[str]], include_distributions: bool }`
- **Output:** `{ row_count: int, column_count: int, duplicate_rows: int, candidate_identifiers: List[str], columns: Dict }`

## 2. `query_data`
- **Purpose:** Validated filtering, grouping, aggregation, sorting, top-$N$, and distinct counts.
- **Input:** `{ group_by: List[str], metrics: List[MetricSpec], filters: List[FilterSpec], sort_by: List[SortSpec], limit: int, sql_filter: Optional[str] }`
- **Output:** `{ columns: List[str], rows: List[Dict], row_count: int, duration_ms: int }`

## 3. `analyze_relationships`
- **Purpose:** Pearson/Spearman correlation and Cramér's V categorical associations with sample sizes and p-values.
- **Input:** `{ method: str, columns: Optional[List[str]], min_sample_size: int }`

## 4. `analyze_trends`
- **Purpose:** Time-series date parsing, period-over-period delta/growth, and rolling averages.
- **Input:** `{ date_column: str, metric_column: str, aggregation: str, period: str, rolling_window: Optional[int], calculate_growth: bool }`

## 5. `detect_anomalies`
- **Purpose:** Univariate IQR bounds and multivariate Isolation Forest detection.
- **Input:** `{ method: str, columns: List[str], contamination: float, threshold: float }`

## 6. `run_statistical_test`
- **Purpose:** Hypothesis testing ($t$-test, Mann–Whitney U, ANOVA, Kruskal–Wallis, Chi-square) with Levene variance checks and effect sizes.
- **Input:** `{ test_type: str, metric_column: str, group_column: Optional[str], alpha: float }`

## 7. `build_baseline_model`
- **Purpose:** Random Forest classification or regression baselines with held-out metrics (accuracy, F1, precision, recall or R2, MAE, RMSE).
- **Input:** `{ target_column: str, feature_columns: Optional[List[str]], model_type: str, test_size: float }`

## 8. `generate_visualization`
- **Purpose:** Produces validated Plotly specifications (bar, line, scatter, histogram, box, heatmap).
- **Input:** `{ chart_type: str, x: Optional[str], y: Optional[str], color: Optional[str], title: Optional[str] }`
