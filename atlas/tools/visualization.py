from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pydantic import BaseModel, Field
from atlas.tools.registry import registry
from atlas.analytics.engine import engine

class GenerateVisualizationInput(BaseModel):
    chart_type: str = Field(description="'bar', 'line', 'scatter', 'histogram', 'box', or 'heatmap'")
    x: Optional[str] = Field(default=None, description="Column for X-axis")
    y: Optional[str] = Field(default=None, description="Column for Y-axis")
    color: Optional[str] = Field(default=None, description="Grouping/color column")
    title: Optional[str] = Field(default=None, description="Chart title")
    limit: int = Field(default=100, description="Max points/bars to display")

@registry.register("generate_visualization", GenerateVisualizationInput)
def generate_visualization(
    dataset_id: str,
    chart_type: str,
    x: Optional[str] = None,
    y: Optional[str] = None,
    color: Optional[str] = None,
    title: Optional[str] = None,
    limit: int = 100
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validated bar, line, scatter, histogram, box, and correlation heatmap specifications rendered through Plotly.
    """
    df = engine.get_dataframe(dataset_id)
    warnings: List[str] = []
    chart_type = chart_type.lower().strip()

    # Column validation
    for col, name in [(x, "x"), (y, "y"), (color, "color")]:
        if col and col not in df.columns:
            return {"error": f"Column '{col}' specified for {name} does not exist in dataset."}, [f"Column {col} missing."]

    clean_df = df.head(limit).copy()
    fig = None
    chart_title = title or f"{chart_type.capitalize()} Chart"

    try:
        if chart_type == "bar":
            if not x:
                return {"error": "Bar chart requires 'x' column."}, ["Missing x."]
            fig = px.bar(clean_df, x=x, y=y, color=color, title=chart_title, template="plotly_dark")

        elif chart_type == "line":
            if not x:
                return {"error": "Line chart requires 'x' column."}, ["Missing x."]
            fig = px.line(clean_df, x=x, y=y, color=color, title=chart_title, template="plotly_dark")

        elif chart_type == "scatter":
            if not x or not y:
                return {"error": "Scatter plot requires both 'x' and 'y' columns."}, ["Missing x or y."]
            fig = px.scatter(clean_df, x=x, y=y, color=color, title=chart_title, template="plotly_dark")

        elif chart_type == "histogram":
            if not x:
                return {"error": "Histogram requires 'x' column."}, ["Missing x."]
            fig = px.histogram(clean_df, x=x, color=color, title=chart_title, template="plotly_dark")

        elif chart_type == "box":
            if not y and not x:
                return {"error": "Box plot requires at least 'x' or 'y' column."}, ["Missing x/y."]
            fig = px.box(clean_df, x=x, y=y, color=color, title=chart_title, template="plotly_dark")

        elif chart_type == "heatmap":
            num_df = df.select_dtypes(include=[np.number])
            if num_df.shape[1] < 2:
                return {"error": "Heatmap requires at least 2 numeric columns."}, ["Insufficient numeric columns."]
            corr = num_df.corr().round(2)
            fig = go.Figure(data=go.Heatmap(
                z=corr.values,
                x=list(corr.columns),
                y=list(corr.index),
                colorscale="Viridis"
            ))
            fig.update_layout(title=chart_title, template="plotly_dark")

        else:
            return {"error": f"Unsupported chart type '{chart_type}'"}, [f"Type {chart_type} unsupported."]

        # Return both JSON schema dict and plotly spec
        fig_dict = fig.to_dict()
        return {
            "chart_type": chart_type,
            "title": chart_title,
            "x": x,
            "y": y,
            "color": color,
            "plotly_figure": fig_dict
        }, warnings

    except Exception as e:
        return {"error": f"Failed to generate visualization: {str(e)}"}, [str(e)]
