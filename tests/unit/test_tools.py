import pytest
from atlas.tools.registry import registry
from atlas.analytics.engine import engine

def test_tool_registry_has_all_eight_tools():
    tools = registry.list_tools()
    expected = [
        "profile_dataset",
        "query_data",
        "analyze_relationships",
        "analyze_trends",
        "detect_anomalies",
        "run_statistical_test",
        "build_baseline_model",
        "generate_visualization"
    ]
    for t in expected:
        assert t in tools, f"Tool '{t}' must be registered in catalogue"

def test_tool_profile_dataset(registered_dataset):
    envelope = registry.execute("profile_dataset", {"include_distributions": True}, dataset_id=registered_dataset)
    assert envelope.status == "success"
    assert envelope.result["row_count"] == 100
    assert "revenue" in envelope.result["columns"]
    assert "mean" in envelope.result["columns"]["revenue"]["distribution"]

def test_tool_query_data(registered_dataset):
    envelope = registry.execute(
        "query_data",
        {
            "group_by": ["region"],
            "metrics": [{"column": "revenue", "aggregation": "sum", "alias": "total_revenue"}],
            "sort_by": [{"column": "total_revenue", "direction": "desc"}],
            "limit": 3
        },
        dataset_id=registered_dataset
    )
    assert envelope.status == "success"
    rows = envelope.result["rows"]
    assert len(rows) <= 3
    assert "total_revenue" in rows[0]

def test_tool_analyze_relationships(registered_dataset):
    envelope = registry.execute(
        "analyze_relationships",
        {"method": "pearson", "columns": ["order_value", "revenue"]},
        dataset_id=registered_dataset
    )
    assert envelope.status == "success"
    assert "significant_pairs" in envelope.result
    # Order value and revenue should have high positive correlation
    pairs = envelope.result["significant_pairs"]
    assert len(pairs) > 0
    assert pairs[0]["correlation"] > 0.8

def test_tool_analyze_trends(registered_dataset):
    envelope = registry.execute(
        "analyze_trends",
        {
            "date_column": "date",
            "metric_column": "revenue",
            "period": "month",
            "calculate_growth": True
        },
        dataset_id=registered_dataset
    )
    assert envelope.status == "success"
    assert envelope.result["data_points"] > 0
    assert "series" in envelope.result

def test_tool_detect_anomalies(registered_dataset):
    envelope = registry.execute(
        "detect_anomalies",
        {"method": "iqr", "columns": ["order_value"], "threshold": 1.5},
        dataset_id=registered_dataset
    )
    assert envelope.status == "success"
    assert envelope.result["anomaly_count"] >= 0
    assert "bounds" in envelope.result

def test_tool_run_statistical_test(registered_dataset):
    envelope = registry.execute(
        "run_statistical_test",
        {
            "test_type": "chi_square",
            "metric_column": "region",
            "group_column": "customer_segment"
        },
        dataset_id=registered_dataset
    )
    assert envelope.status == "success"
    assert "p_value" in envelope.result
    assert "statistic" in envelope.result

def test_tool_build_baseline_model(registered_dataset):
    envelope = registry.execute(
        "build_baseline_model",
        {
            "target_column": "churn",
            "model_type": "classification",
            "test_size": 0.2
        },
        dataset_id=registered_dataset
    )
    assert envelope.status == "success"
    metrics = envelope.result["held_out_metrics"]
    assert "accuracy" in metrics

def test_tool_generate_visualization(registered_dataset):
    envelope = registry.execute(
        "generate_visualization",
        {
            "chart_type": "bar",
            "x": "region",
            "y": "revenue",
            "title": "Revenue by Region"
        },
        dataset_id=registered_dataset
    )
    assert envelope.status == "success"
    assert "plotly_figure" in envelope.result
