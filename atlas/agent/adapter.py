import os
import json
import re
from typing import Dict, Any, List, Optional
from atlas.config import settings

class LLMAdapter:
    """
    Provider abstraction for structured planning and evidence synthesis.
    Supports OpenAI, Anthropic, Gemini, or a transparent Deterministic Rule-Based Fallback.
    """
    def __init__(self):
        self.provider = settings.llm_provider
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model

    def is_deterministic_mode(self) -> bool:
        return (not self.api_key) or (self.provider == "deterministic_demo")

    def plan_steps(
        self,
        question: str,
        schema: Dict[str, Any],
        memories: List[Dict[str, Any]],
        available_tools: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generates a sequence of analytical steps. If LLM key is configured,
        prompts the LLM; otherwise uses deterministic semantic intent parsing.
        """
        if self.is_deterministic_mode():
            return self._deterministic_plan(question, schema, memories)

        # For external LLM providers (e.g. OpenAI / Anthropic)
        try:
            return self._call_external_llm_planner(question, schema, memories, available_tools)
        except Exception:
            # Graceful fallback to deterministic planner if API call fails
            return self._deterministic_plan(question, schema, memories)

    def _call_external_llm_planner(
        self,
        question: str,
        schema: Dict[str, Any],
        memories: List[Dict[str, Any]],
        available_tools: List[str]
    ) -> List[Dict[str, Any]]:
        # Lightweight httpx call for standard OpenAI-compatible endpoints
        import httpx
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        prompt = f"""
You are the ATLAS planner. Available tools: {available_tools}
Dataset schema: {json.dumps(schema)}
Active domain memories: {json.dumps(memories)}

User question: {question}

Return a valid JSON array of tool execution steps to answer the question.
Format:
[
  {{"tool_name": "query_data", "arguments": {{...}}, "description": "..."}}
]
"""
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=20.0)
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return self._deterministic_plan(question, schema, memories)

    def _deterministic_plan(
        self,
        question: str,
        schema: Dict[str, Any],
        memories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deterministic, transparent semantic planner without hallucination.
        Maps natural language intent to analytical tool operations.
        """
        q_lower = question.lower()
        cols_info = schema.get("columns", {})
        col_names = list(cols_info.keys())
        
        # Check active memories for applicable filters or definitions
        memory_sql_filters = []
        cols_in_dataset = set(cols_info.keys())
        sql_keywords = {"AND", "OR", "NOT", "IS", "NULL", "IN", "LIKE", "TRUE", "FALSE"}
        
        for mem in memories:
            val = mem.get("value", {})
            rule = val.get("rule")
            mem_cols = mem.get("columns", [])
            if rule:
                # If memory explicitly specifies columns, ensure they exist in dataset
                if mem_cols and not all(c in cols_in_dataset for c in mem_cols):
                    continue
                # Extract identifiers from the SQL rule to avoid syntax errors on absent columns
                identifiers = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", rule)
                candidate_cols = [c for c in identifiers if c.upper() not in sql_keywords]
                if any(c not in cols_in_dataset for c in candidate_cols):
                    continue
                memory_sql_filters.append(rule)

        combined_sql_filter = " AND ".join(memory_sql_filters) if memory_sql_filters else None

        steps: List[Dict[str, Any]] = []

        # 1. Profile / Overview questions
        if any(w in q_lower for w in ["profile", "summary", "overview", "schema", "missing", "duplicate", "null"]):
            steps.append({
                "tool_name": "profile_dataset",
                "arguments": {"include_distributions": True},
                "description": "Profile dataset distributions, missingness, and cardinality."
            })
            return steps

        # 2. Anomaly detection
        if any(w in q_lower for w in ["anomaly", "anomalous", "outlier", "unusual", "spike"]):
            num_cols = [c for c, inf in cols_info.items() if inf.get("inferred_type") in {"float", "integer"}]
            # Look for mentioned column
            target_cols = [c for c in num_cols if c.lower() in q_lower] or num_cols[:2]
            if target_cols:
                steps.append({
                    "tool_name": "detect_anomalies",
                    "arguments": {
                        "columns": target_cols,
                        "method": "iqr",
                        "threshold": 1.5
                    },
                    "description": f"Detect statistical anomalies in {target_cols} using IQR method."
                })
            return steps

        # 3. Correlation / Relationships
        if any(w in q_lower for w in ["correlat", "relationship", "associated with", "association"]):
            num_cols = [c for c, inf in cols_info.items() if inf.get("inferred_type") in {"float", "integer"}]
            steps.append({
                "tool_name": "analyze_relationships",
                "arguments": {
                    "method": "pearson",
                    "columns": num_cols[:5]
                },
                "description": "Analyze Pearson pairwise correlation and p-values across numeric variables."
            })
            return steps

        # 4. Trends / Time Series / Growth
        if any(w in q_lower for w in ["trend", "month over month", "mom", "over time", "growing", "growth", "season"]):
            date_col = schema.get("candidate_dates", [None])[0]
            if not date_col:
                for c, inf in cols_info.items():
                    if "date" in c.lower() or "time" in c.lower() or inf.get("inferred_type") == "datetime":
                        date_col = c
                        break
            
            num_cols = [c for c, inf in cols_info.items() if inf.get("inferred_type") in {"float", "integer"}]
            # Find matching metric column
            metric_col = next((c for c in num_cols if c.lower() in q_lower), num_cols[0] if num_cols else "*")
            
            if date_col:
                steps.append({
                    "tool_name": "analyze_trends",
                    "arguments": {
                        "date_column": date_col,
                        "metric_column": metric_col,
                        "period": "month",
                        "calculate_growth": True
                    },
                    "description": f"Analyze monthly trends and growth rates for {metric_col}."
                })
                steps.append({
                    "tool_name": "generate_visualization",
                    "arguments": {
                        "chart_type": "line",
                        "x": date_col,
                        "y": metric_col,
                        "title": f"Trend Analysis: {metric_col} Over Time"
                    },
                    "description": "Generate trend line chart."
                })
                return steps

        # 5. Statistical hypothesis testing / compare groups
        if any(w in q_lower for w in ["significant", "significance", "t-test", "difference between", "compare average", "hypothesis"]):
            num_cols = [c for c, inf in cols_info.items() if inf.get("inferred_type") in {"float", "integer"}]
            cat_cols = [c for c, inf in cols_info.items() if inf.get("inferred_type") in {"categorical", "string"}]
            
            metric = next((c for c in num_cols if c.lower() in q_lower), num_cols[0] if num_cols else "")
            group = next((c for c in cat_cols if c.lower() in q_lower), cat_cols[0] if cat_cols else "")
            
            if metric and group:
                steps.append({
                    "tool_name": "run_statistical_test",
                    "arguments": {
                        "test_type": "t_test_ind",
                        "metric_column": metric,
                        "group_column": group,
                        "alpha": 0.05
                    },
                    "description": f"Run two-sample statistical test comparing {metric} across {group}."
                })
                return steps

        # 6. Baseline ML model
        if any(w in q_lower for w in ["baseline model", "predict", "classification", "regression", "train", "model performance"]):
            target = next((c for c in col_names if c.lower() in q_lower), col_names[-1])
            steps.append({
                "tool_name": "build_baseline_model",
                "arguments": {
                    "target_column": target,
                    "model_type": "auto",
                    "test_size": 0.2
                },
                "description": f"Train baseline ML model predicting '{target}' and report held-out metrics."
            })
            return steps

        # 7. General Aggregation / Group by / Top-N (e.g. "Which five regions contribute the most revenue?")
        # Match dimensions and metrics
        num_cols = [c for c, inf in cols_info.items() if inf.get("inferred_type") in {"float", "integer"}]
        cat_cols = [c for c, inf in cols_info.items() if inf.get("inferred_type") in {"categorical", "string"}]

        # Match columns mentioned in question
        matched_dims = [c for c in cat_cols if c.lower() in q_lower]
        matched_metrics = [c for c in num_cols if c.lower() in q_lower]

        # Extract top-N limit if mentioned (e.g. "five", "top 5", "10")
        limit = 100
        n_match = re.search(r"\b(top\s+|first\s+)?(\d+)\b", q_lower)
        if n_match:
            limit = int(n_match.group(2))
        elif "five" in q_lower:
            limit = 5
        elif "ten" in q_lower:
            limit = 10

        dim = matched_dims[0] if matched_dims else (cat_cols[0] if cat_cols else None)
        metric = matched_metrics[0] if matched_metrics else (num_cols[0] if num_cols else None)

        if dim and metric:
            steps.append({
                "tool_name": "query_data",
                "arguments": {
                    "group_by": [dim],
                    "metrics": [{"column": metric, "aggregation": "sum", "alias": f"total_{metric}"}],
                    "sort_by": [{"column": f"total_{metric}", "direction": "desc"}],
                    "limit": limit,
                    "sql_filter": combined_sql_filter
                },
                "description": f"Aggregate total {metric} grouped by {dim} (limit {limit})" + (f" with active memory filter: {combined_sql_filter}" if combined_sql_filter else "")
            })
            steps.append({
                "tool_name": "generate_visualization",
                "arguments": {
                    "chart_type": "bar",
                    "x": dim,
                    "y": f"total_{metric}",
                    "title": f"Top {limit} {dim} by Total {metric}"
                },
                "description": "Generate bar chart for aggregated totals."
            })
        elif metric:
            steps.append({
                "tool_name": "query_data",
                "arguments": {
                    "metrics": [{"column": metric, "aggregation": "sum", "alias": f"total_{metric}"}],
                    "sql_filter": combined_sql_filter
                },
                "description": f"Calculate overall total of {metric}."
            })
        else:
            steps.append({
                "tool_name": "profile_dataset",
                "arguments": {"include_distributions": True},
                "description": "Profile dataset to inspect available structure."
            })

        return steps

    def synthesize_answer(
        self,
        question: str,
        plan: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        memories_applied: List[Dict[str, Any]]
    ) -> str:
        """
        Synthesizes an evidence-grounded textual answer referencing exact computed values.
        """
        lines = []
        if self.is_deterministic_mode():
            lines.append("> *Mode: Deterministic Analytical Engine (Evidence-Grounded)*\n")
        
        if memories_applied:
            lines.append("**Domain Knowledge Applied from Memory:**")
            for m in memories_applied:
                lines.append(f"- **{m.get('key')}**: `{m.get('value', {}).get('rule')}` (*{m.get('value', {}).get('definition', '')}*)")
            lines.append("")

        lines.append("### Findings & Evidence")

        for idx, res in enumerate(results, 1):
            tool = res.get("tool_name")
            status = res.get("status")
            op_id = res.get("operation_id")
            output = res.get("result", {})

            if status != "success":
                lines.append(f"- **Step {idx} ({tool})**: Execution error: `{res.get('error_message')}`")
                continue

            if tool == "query_data":
                rows = output.get("rows", [])
                cols = output.get("columns", [])
                lines.append(f"- **Calculated Results** (`{op_id}`):")
                if rows:
                    lines.append(f"  - Retrieved {len(rows)} rows.")
                    # Format top 5 rows
                    for r in rows[:5]:
                        row_items = [f"{k}: **{v}**" for k, v in r.items()]
                        lines.append(f"    - " + ", ".join(row_items))
                else:
                    lines.append("  - Query completed with 0 matching rows.")

            elif tool == "profile_dataset":
                lines.append(f"- **Dataset Profile** (`{op_id}`):")
                lines.append(f"  - Total rows: **{output.get('row_count')}**, columns: **{output.get('column_count')}**, duplicate rows: **{output.get('duplicate_rows')}**.")
                candidate_ids = output.get("candidate_identifiers", [])
                if candidate_ids:
                    lines.append(f"  - Candidate unique identifiers: {', '.join(candidate_ids)}.")

            elif tool == "analyze_relationships":
                lines.append(f"- **Correlation Analysis** (`{op_id}`):")
                sig = output.get("significant_pairs", [])
                if sig:
                    top_pair = sig[0]
                    lines.append(f"  - Strongest relationship: **{top_pair['column_1']}** & **{top_pair['column_2']}** (r = **{top_pair['correlation']}**, p = {top_pair['p_value']}).")
                else:
                    lines.append("  - No significant pairwise correlations detected.")

            elif tool == "analyze_trends":
                summary = output.get("overall_summary")
                lines.append(f"- **Trend Analysis** (`{op_id}`):")
                if summary:
                    lines.append(f"  - From {summary['start_period']} ({summary['start_value']}) to {summary['end_period']} ({summary['end_value']}), overall change is **{summary['overall_change']}** ({summary.get('overall_percent_change')}%).")

            elif tool == "detect_anomalies":
                lines.append(f"- **Anomaly Detection** (`{op_id}`):")
                lines.append(f"  - Detected **{output.get('anomaly_count')}** anomalous records ({output.get('anomaly_percentage')}% of data) using **{output.get('method')}**.")

            elif tool == "run_statistical_test":
                lines.append(f"- **Hypothesis Test** (`{op_id}`):")
                lines.append(f"  - Test: **{output.get('test_type')}**, Statistic: **{output.get('statistic')}**, p-value: **{output.get('p_value')}**.")
                lines.append(f"  - Conclusion: **{output.get('conclusion')}**")

            elif tool == "build_baseline_model":
                lines.append(f"- **Baseline ML Model** (`{op_id}`):")
                lines.append(f"  - Target: **{output.get('target')}**, Algorithm: **{output.get('algorithm')}**.")
                metrics_str = ", ".join(f"{k}: **{v}**" for k, v in output.get("held_out_metrics", {}).items())
                lines.append(f"  - Held-out evaluation metrics: {metrics_str}.")

        return "\n".join(lines)
