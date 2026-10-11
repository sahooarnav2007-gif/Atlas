# ATLAS Demonstration Questions & Verification Scenarios

This document contains canonical analytical questions demonstrating the core capabilities of ATLAS against `customer_sales_v1.csv` and `customer_sales_v2.csv`.

---

### Scenario 1: Grouping & Aggregation with Top-N
- **Question:** `Which five regions contribute the most revenue?`
- **Expected Tool:** `query_data` + `generate_visualization` (bar chart)
- **Verification:** Grouped by `region`, SUM(`revenue`) ordered descending, limit 5. All numbers grounded in computed values.

---

### Scenario 2: Unseen Dataset Profiling & Anomaly Detection
- **Question:** `Find anomalous transactions and explain the detection method.`
- **Expected Tool:** `detect_anomalies`
- **Verification:** Detects injected 12x order value spikes with IQR method bounds ($[Q1 - 1.5 \times IQR, Q3 + 1.5 \times IQR]$).

---

### Scenario 3: Statistical Hypothesis Testing
- **Question:** `Compare average order value across customer segments and assess whether differences are statistically significant.`
- **Expected Tool:** `run_statistical_test`
- **Verification:** Computes test statistic, exact p-value, Levene assumption tests, and effect sizes (Cohen's d or ANOVA F-ratio).

---

### Scenario 4: Time Series & Trend Analysis
- **Question:** `Is revenue growing month over month?`
- **Expected Tool:** `analyze_trends` + `generate_visualization` (line chart)
- **Verification:** Parses dates, aggregates monthly, computes period-over-period delta and percent growth.

---

### Scenario 5: Correlation & Relationship Analysis
- **Question:** `Which variables are most strongly associated with churn?`
- **Expected Tool:** `analyze_relationships`
- **Verification:** Computes correlation matrix, p-values, sample sizes, and identifies top correlated pairs.

---

### Scenario 6: Baseline Predictive Model
- **Question:** `Build a baseline model for an explicitly selected target and report held-out performance.`
- **Expected Tool:** `build_baseline_model`
- **Verification:** 80/20 train/test split, Random Forest classifier, held-out accuracy, precision, recall, and F1 score.

---

### Scenario 7: Cross-Session Persistent Domain Memory
1. **Session A:**
   - Define metric: `active_customer` with rule `customer_status != 'cancelled'`.
   - Run: `Which five regions contribute the most revenue?`
   - Notice: Revenue total only sums rows where `customer_status != 'cancelled'`.
2. **Session B:**
   - Upload new dataset version: `customer_sales_v2.csv`.
   - Ask: `Which five regions contribute the most revenue?`
   - Result: Agent automatically retrieves the persistent rule from PostgreSQL/SQLite, applies the filter, and shows the modified calculation in the provenance trace.
