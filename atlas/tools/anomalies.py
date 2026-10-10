from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from pydantic import BaseModel, Field
from atlas.tools.registry import registry
from atlas.analytics.engine import engine

class DetectAnomaliesInput(BaseModel):
    method: str = Field(default="iqr", description="'iqr', 'zscore', or 'isolation_forest'")
    columns: List[str] = Field(description="Columns to evaluate for anomalies")
    contamination: float = Field(default=0.05, description="Expected proportion of outliers for isolation forest (0.01 to 0.5)")
    threshold: float = Field(default=1.5, description="IQR multiplier or Z-score cutoff")

@registry.register("detect_anomalies", DetectAnomaliesInput)
def detect_anomalies(
    dataset_id: str,
    columns: List[str],
    method: str = "iqr",
    contamination: float = 0.05,
    threshold: float = 1.5
) -> Tuple[Dict[str, Any], List[str]]:
    """
    IQR/robust univariate detection and Isolation Forest for suitable multivariate numeric data.
    """
    df = engine.get_dataframe(dataset_id)
    warnings: List[str] = []
    method = method.lower().strip()

    valid_cols = [c for c in columns if c in df.columns]
    if not valid_cols:
        return {"error": "None of the specified columns exist in the dataset."}, ["No valid columns found."]

    num_df = df[valid_cols].apply(pd.to_numeric, errors="coerce")
    clean_indices = num_df.dropna().index

    if len(clean_indices) < 5:
        return {"error": "Insufficient valid numeric rows for anomaly detection."}, ["Insufficient data."]

    if method == "iqr":
        # Univariate / multi-column IQR
        outlier_mask = pd.Series(False, index=df.index)
        column_bounds = {}
        for col in valid_cols:
            s = num_df[col].dropna()
            q25 = float(s.quantile(0.25))
            q75 = float(s.quantile(0.75))
            iqr = q75 - q25
            lower_bound = q25 - threshold * iqr
            upper_bound = q75 + threshold * iqr
            col_outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
            outlier_mask = outlier_mask | col_outliers
            column_bounds[col] = {
                "q25": round(q25, 2),
                "q75": round(q75, 2),
                "iqr": round(iqr, 2),
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
                "outlier_count": int(col_outliers.sum())
            }

        anomalous_rows = df[outlier_mask].head(50)
        return {
            "method": "iqr",
            "threshold_multiplier": threshold,
            "bounds": column_bounds,
            "total_evaluated_rows": len(df),
            "anomaly_count": int(outlier_mask.sum()),
            "anomaly_percentage": round(float(outlier_mask.mean()) * 100, 2),
            "sample_anomalies": anomalous_rows.to_dict(orient="records")
        }, warnings

    elif method == "zscore":
        means = num_df.mean()
        stds = num_df.std()
        z_scores = ((num_df - means) / stds).abs()
        outlier_mask = (z_scores > threshold).any(axis=1)

        anomalous_rows = df[outlier_mask].head(50)
        return {
            "method": "zscore",
            "threshold": threshold,
            "total_evaluated_rows": len(df),
            "anomaly_count": int(outlier_mask.sum()),
            "anomaly_percentage": round(float(outlier_mask.mean()) * 100, 2),
            "sample_anomalies": anomalous_rows.to_dict(orient="records")
        }, warnings

    elif method == "isolation_forest":
        sub_df = num_df.loc[clean_indices]
        iso = IsolationForest(contamination=contamination, random_state=42)
        preds = iso.fit_predict(sub_df)
        scores = iso.decision_function(sub_df)

        is_outlier = (preds == -1)
        anomaly_indices = sub_df.index[is_outlier]
        anomalies_df = df.loc[anomaly_indices].copy()
        anomalies_df["anomaly_score"] = scores[is_outlier].round(4)
        anomalies_df = anomalies_df.sort_values("anomaly_score")

        return {
            "method": "isolation_forest",
            "contamination": contamination,
            "total_evaluated_rows": len(sub_df),
            "anomaly_count": int(is_outlier.sum()),
            "anomaly_percentage": round(float(is_outlier.mean()) * 100, 2),
            "sample_anomalies": anomalies_df.head(50).to_dict(orient="records")
        }, warnings
    else:
        return {"error": f"Unknown anomaly detection method '{method}'"}, [f"Method {method} unsupported."]
