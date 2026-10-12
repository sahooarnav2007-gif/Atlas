import pytest
import json
from atlas.agent.orchestrator import orchestrator
from atlas.agent.adapter import LLMAdapter
from atlas.persistence.db import SessionFactory, DatasetRecord

def test_deterministic_planner_generates_valid_steps(registered_dataset):
    adapter = LLMAdapter()
    schema = {
        "columns": {
            "region": {"inferred_type": "categorical"},
            "revenue": {"inferred_type": "float"}
        }
    }
    steps = adapter.plan_steps(
        question="Which five regions contribute the most revenue?",
        schema=schema,
        memories=[],
        available_tools=["query_data", "generate_visualization"]
    )
    assert len(steps) >= 1
    assert steps[0]["tool_name"] == "query_data"
    assert steps[0]["arguments"]["group_by"] == ["region"]

def test_agent_orchestrator_end_to_end(registered_dataset):
    db = SessionFactory()
    # Ensure dataset record exists in DB
    rec = DatasetRecord(
        dataset_id=registered_dataset,
        filename="sales.csv",
        file_path="mock/path",
        file_size_bytes=1000,
        row_count=100,
        column_count=8,
        version="v1",
        dataset_family="customer_sales",
        schema_info=json.dumps({
            "columns": {
                "region": {"inferred_type": "categorical"},
                "revenue": {"inferred_type": "float"}
            }
        })
    )
    db.merge(rec)
    db.commit()
    db.close()

    result = orchestrator.run_analysis(
        dataset_id=registered_dataset,
        question="Which five regions contribute the most revenue?"
    )

    assert result["status"] == "completed"
    assert "answer" in result
    assert len(result["execution_trace"]) > 0
    assert result["execution_trace"][0]["status"] == "success"
