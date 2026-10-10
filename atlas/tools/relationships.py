from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from pydantic import BaseModel, Field
from atlas.tools.registry import registry
from atlas.analytics.engine import engine

class AnalyzeRelationshipsInput(BaseModel):
    method: str = Field(default="pearson", description="'pearson', 'spearman', or 'cramers_v'")
    columns: Optional[List[str]] = Field(default=None, description="Subset of columns to analyze")
    min_sample_size: int = Field(default=5, description="Minimum rows required for valid correlation")

def calculate_cramers_v(x: pd.Series, y: pd.Series) -> float:
    confusion_matrix = pd.crosstab(x, y)
    chi2 = stats.chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    r, k = confusion_matrix.shape
    if n == 0 or min(r - 1, k - 1) == 0:
        return 0.0
    return float(np.sqrt((chi2 / n) / min(r - 1, k - 1)))

@registry.register("analyze_relationships", AnalyzeRelationshipsInput)
def analyze_relationships(
    dataset_id: str,
    method: str = "pearson",
    columns: Optional[List[str]] = None,
    min_sample_size: int = 5
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Pearson/Spearman correlation and suitable categorical association measures with sample sizes.
    """
    df = engine.get_dataframe(dataset_id)
    warnings: List[str] = []
    method = method.lower().strip()

    if method in {"pearson", "spearman"}:
        numeric_df = df.select_dtypes(include=[np.number])
        if columns:
            valid_cols = [c for c in columns if c in numeric_df.columns]
            if len(valid_cols) < len(columns):
                warnings.append("Some requested columns are non-numeric or missing and were excluded.")
            numeric_df = numeric_df[valid_cols]

        if numeric_df.shape[1] < 2:
            return {
                "error": "At least 2 numeric columns are required for correlation analysis.",
                "correlation_matrix": {},
                "significant_pairs": []
            }, warnings + ["Insufficient numeric columns for correlation analysis."]

        clean_df = numeric_df.dropna()
        sample_size = len(clean_df)
        if sample_size < min_sample_size:
            warnings.append(f"Sample size ({sample_size}) is below threshold of {min_sample_size}.")

        cols = list(clean_df.columns)
        corr_matrix: Dict[str, Dict[str, float]] = {c: {} for c in cols}
        pairs: List[Dict[str, Any]] = []

        for i in range(len(cols)):
            col1 = cols[i]
            for j in range(i, len(cols)):
                col2 = cols[j]
                if col1 == col2:
                    corr_matrix[col1][col2] = 1.0
                    continue

                x, y = clean_df[col1], clean_df[col2]
                if method == "spearman":
                    res = stats.spearmanr(x, y)
                else:
                    res = stats.pearsonr(x, y)

                r_val = float(res.statistic) if not np.isnan(res.statistic) else 0.0
                p_val = float(res.pvalue) if not np.isnan(res.pvalue) else 1.0

                corr_matrix[col1][col2] = round(r_val, 4)
                corr_matrix[col2][col1] = round(r_val, 4)

                pairs.append({
                    "column_1": col1,
                    "column_2": col2,
                    "correlation": round(r_val, 4),
                    "p_value": round(p_val, 5),
                    "significant": p_val < 0.05,
                    "sample_size": sample_size
                })

        pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)

        return {
            "method": method,
            "sample_size": sample_size,
            "columns": cols,
            "correlation_matrix": corr_matrix,
            "significant_pairs": pairs
        }, warnings

    elif method == "cramers_v":
        cat_df = df.select_dtypes(include=[object, "category"])
        if columns:
            valid_cols = [c for c in columns if c in cat_df.columns]
            cat_df = cat_df[valid_cols]

        if cat_df.shape[1] < 2:
            return {
                "error": "At least 2 categorical columns required for Cramér's V.",
                "association_matrix": {}
            }, warnings + ["Insufficient categorical columns."]

        cols = list(cat_df.columns)
        matrix: Dict[str, Dict[str, float]] = {c: {} for c in cols}
        for i in range(len(cols)):
            for j in range(len(cols)):
                c1, c2 = cols[i], cols[j]
                if c1 == c2:
                    matrix[c1][c2] = 1.0
                else:
                    pair_df = cat_df[[c1, c2]].dropna()
                    val = calculate_cramers_v(pair_df[c1], pair_df[c2]) if len(pair_df) > 0 else 0.0
                    matrix[c1][c2] = round(val, 4)

        return {
            "method": "cramers_v",
            "columns": cols,
            "association_matrix": matrix
        }, warnings
    else:
        return {"error": f"Unsupported method '{method}'"}, warnings + [f"Method {method} unsupported."]
