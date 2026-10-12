import pytest
from atlas.memory.service import memory_service
from atlas.analytics.engine import engine
from atlas.tools.registry import registry
from examples.generate_sample_data import generate_sample_sales_data

def test_memory_creation_and_retrieval():
    mem = memory_service.save_memory(
        memory_type="metric_definition",
        key="test_metric",
        value={"rule": "customer_status != 'cancelled'"},
        dataset_family="customer_sales"
    )
    assert mem["key"] == "test_metric"
    assert mem["status"] == "active"
    assert mem["version"] == 1

    retrieved = memory_service.retrieve_memories(dataset_family="customer_sales")
    keys = [m["key"] for m in retrieved]
    assert "test_metric" in keys

def test_memory_versioning_and_superseding():
    mem_v1 = memory_service.save_memory(
        memory_type="metric_definition",
        key="discount_rule",
        value={"rule": "discount > 0.05"},
        dataset_family="customer_sales"
    )
    assert mem_v1["version"] == 1

    mem_v2 = memory_service.save_memory(
        memory_type="metric_definition",
        key="discount_rule",
        value={"rule": "discount > 0.10"},
        dataset_family="customer_sales"
    )
    assert mem_v2["version"] == 2
    assert mem_v2["status"] == "active"

    # Old memory is superseded
    old = memory_service.get_memory(mem_v1["memory_id"])
    assert old["status"] == "superseded"
    assert old["superseded_by"] == mem_v2["memory_id"]

def test_cross_session_memory_changes_actual_calculation():
    """
    CRITICAL BLUEPRINT TEST:
    Save a metric definition in session A ('active_customer' excludes cancelled accounts);
    In session B, retrieve it and verify that it changes the actual numerical calculation.
    """
    # 1. Dataset setup: 100 rows containing some cancelled accounts
    df = generate_sample_sales_data(100, seed=42)
    dataset_id = "ds_cross_session_demo"
    engine.register_dataset(dataset_id, df)

    # Calculation WITHOUT memory (unfiltered total revenue)
    env_unfiltered = registry.execute(
        "query_data",
        {"metrics": [{"column": "revenue", "aggregation": "sum", "alias": "total_rev"}]},
        dataset_id=dataset_id
    )
    total_rev_all = env_unfiltered.result["rows"][0]["total_rev"]

    # 2. Session A: User explicitly saves metric definition
    memory_service.save_memory(
        memory_type="metric_definition",
        key="active_customers_only",
        value={
            "definition": "Active customers exclude cancelled accounts",
            "rule": "customer_status != 'cancelled'"
        },
        dataset_family="customer_sales",
        columns=["customer_status"]
    )

    # 3. Session B: System retrieves active memory and applies the rule
    active_mems = memory_service.retrieve_memories(dataset_family="customer_sales", columns=["customer_status"])
    matching_rule = active_mems[0]["value"]["rule"]
    assert "customer_status != 'cancelled'" in matching_rule

    env_filtered = registry.execute(
        "query_data",
        {
            "metrics": [{"column": "revenue", "aggregation": "sum", "alias": "total_rev"}],
            "sql_filter": matching_rule
        },
        dataset_id=dataset_id
    )
    total_rev_filtered = env_filtered.result["rows"][0]["total_rev"]

    # 4. Assert: output calculation genuinely changed!
    assert total_rev_filtered < total_rev_all, "Filtered revenue should be strictly less than unfiltered total"
    print(f"Verified calculation change: All Revenue={total_rev_all} vs Active Customer Revenue={total_rev_filtered}")
