from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from pydantic import BaseModel, Field
from atlas.tools.registry import registry
from atlas.analytics.engine import engine

class ProfileDatasetInput(BaseModel):
    columns: Optional[List[str]] = Field(default=None, description="Subset of columns to profile")
    include_distributions: bool = Field(default=True, description="Compute numeric percentiles and category distributions")

@registry.register("profile_dataset", ProfileDatasetInput)
def profile_dataset(dataset_id: str, columns: Optional[List[str]] = None, include_distributions: bool = True) -> Tuple[Dict[str, Any], List[str]]:
    """
    Discover types, missingness, cardinality, duplicates, candidate identifiers, dates, and distributions.
    """
    df = engine.get_dataframe(dataset_id)
    warnings: List[str] = []

    target_cols = columns if columns else list(df.columns)
    for col in target_cols:
        if col not in df.columns:
            warnings.append(f"Column '{col}' not found in dataset; skipped.")

    active_cols = [c for c in target_cols if c in df.columns]
    total_rows = len(df)
    duplicates = int(df.duplicated().sum())

    profiles: Dict[str, Any] = {}
    candidate_ids: List[str] = []
    candidate_dates: List[str] = []

    for col in active_cols:
        series = df[col]
        missing_count = int(series.isna().sum())
        missing_pct = round((missing_count / total_rows) * 100, 2) if total_rows > 0 else 0.0
        n_unique = int(series.nunique(dropna=True))

        info: Dict[str, Any] = {
            "name": col,
            "data_type": str(series.dtype),
            "missing_count": missing_count,
            "missing_pct": missing_pct,
            "distinct_count": n_unique
        }

        if missing_count == 0 and n_unique == total_rows and total_rows > 1:
            candidate_ids.append(col)

        if pd.api.types.is_numeric_dtype(series):
            info["type_category"] = "numeric"
            if include_distributions and not series.dropna().empty:
                desc = series.describe()
                info["distribution"] = {
                    "mean": float(desc.get("mean", 0)),
                    "std": float(desc.get("std", 0)),
                    "min": float(desc.get("min", 0)),
                    "p25": float(desc.get("25%", 0)),
                    "median": float(desc.get("50%", 0)),
                    "p75": float(desc.get("75%", 0)),
                    "max": float(desc.get("max", 0))
                }
        else:
            # Check date/time
            try:
                sample = series.dropna().head(20)
                if not sample.empty:
                    pd.to_datetime(sample, errors="raise")
                    candidate_dates.append(col)
                    info["type_category"] = "datetime"
                else:
                    info["type_category"] = "categorical"
            except Exception:
                info["type_category"] = "categorical"

            if include_distributions and not series.dropna().empty:
                top_counts = series.value_counts().head(5).to_dict()
                info["top_categories"] = {str(k): int(v) for k, v in top_counts.items()}

        profiles[col] = info

    result = {
        "dataset_id": dataset_id,
        "row_count": total_rows,
        "column_count": len(df.columns),
        "duplicate_rows": duplicates,
        "candidate_identifiers": candidate_ids,
        "candidate_dates": candidate_dates,
        "columns": profiles
    }
    return result, warnings
