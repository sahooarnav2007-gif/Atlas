from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from atlas.tools.registry import registry
from atlas.analytics.engine import engine

class AnalyzeTrendsInput(BaseModel):
    date_column: str = Field(description="Name of the datetime column")
    metric_column: str = Field(description="Name of the numeric column to aggregate")
    aggregation: str = Field(default="sum", description="'sum', 'mean', or 'count'")
    period: str = Field(default="month", description="'day', 'week', 'month', 'quarter', or 'year'")
    rolling_window: Optional[int] = Field(default=None, description="Rolling window size in periods")
    calculate_growth: bool = Field(default=True, description="Compute period-over-period growth rates")

@registry.register("analyze_trends", AnalyzeTrendsInput)
def analyze_trends(
    dataset_id: str,
    date_column: str,
    metric_column: str,
    aggregation: str = "sum",
    period: str = "month",
    rolling_window: Optional[int] = None,
    calculate_growth: bool = True
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Date parsing, time grouping, period-over-period changes, rolling summaries, and supported seasonality analysis.
    """
    df = engine.get_dataframe(dataset_id)
    warnings: List[str] = []

    if date_column not in df.columns:
        return {"error": f"Date column '{date_column}' not found."}, [f"Column {date_column} missing."]
    if metric_column not in df.columns and metric_column != "*":
        return {"error": f"Metric column '{metric_column}' not found."}, [f"Column {metric_column} missing."]

    clean_df = df.copy()
    try:
        clean_df[date_column] = pd.to_datetime(clean_df[date_column], errors="coerce")
    except Exception as e:
        return {"error": f"Failed to parse dates in column '{date_column}': {str(e)}"}, [str(e)]

    invalid_dates = clean_df[date_column].isna().sum()
    if invalid_dates > 0:
        warnings.append(f"Dropped {invalid_dates} rows with unparseable or null dates.")
        clean_df = clean_df.dropna(subset=[date_column])

    if clean_df.empty:
        return {"error": "No valid dates found in dataset."}, warnings

    if metric_column != "*":
        clean_df[metric_column] = pd.to_numeric(clean_df[metric_column], errors="coerce")
        clean_df = clean_df.dropna(subset=[metric_column])

    # Period frequency map
    freq_map = {
        "day": "D",
        "week": "W",
        "month": "MS",
        "quarter": "QS",
        "year": "YS"
    }
    freq = freq_map.get(period.lower(), "MS")

    # Set datetime index
    clean_df = clean_df.set_index(date_column).sort_index()

    # Resample and aggregate
    agg_fn = aggregation.lower()
    if metric_column == "*":
        series = clean_df.resample(freq).size()
    else:
        if agg_fn in {"mean", "avg"}:
            series = clean_df[metric_column].resample(freq).mean()
        elif agg_fn == "count":
            series = clean_df[metric_column].resample(freq).count()
        else:
            series = clean_df[metric_column].resample(freq).sum()

    res_df = pd.DataFrame({
        "period": series.index.strftime("%Y-%m-%d"),
        "value": series.values
    })

    if calculate_growth and len(res_df) > 1:
        res_df["prior_period_value"] = res_df["value"].shift(1)
        res_df["absolute_change"] = res_df["value"] - res_df["prior_period_value"]
        res_df["percent_growth"] = (res_df["absolute_change"] / res_df["prior_period_value"].replace(0, np.nan)) * 100
        res_df["percent_growth"] = res_df["percent_growth"].round(2)

    if rolling_window and rolling_window > 1:
        res_df[f"rolling_{rolling_window}_mean"] = res_df["value"].rolling(rolling_window).mean().round(2)

    # Basic trend direction
    overall_growth = None
    if len(res_df) >= 2:
        start_val = res_df["value"].iloc[0]
        end_val = res_df["value"].iloc[-1]
        overall_change = end_val - start_val
        overall_pct = ((overall_change / start_val) * 100) if start_val != 0 else None
        overall_growth = {
            "start_period": res_df["period"].iloc[0],
            "end_period": res_df["period"].iloc[-1],
            "start_value": round(float(start_val), 2),
            "end_value": round(float(end_val), 2),
            "overall_change": round(float(overall_change), 2),
            "overall_percent_change": round(float(overall_pct), 2) if overall_pct is not None else None
        }

    return {
        "date_column": date_column,
        "metric_column": metric_column,
        "aggregation": aggregation,
        "period": period,
        "data_points": len(res_df),
        "overall_summary": overall_growth,
        "series": res_df.replace({np.nan: None}).to_dict(orient="records")
    }, warnings
