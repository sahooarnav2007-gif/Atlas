import pytest
import pandas as pd
import numpy as np
from atlas.ingestion.parser import DatasetParser
from atlas.analytics.engine import engine
from atlas.tools.registry import registry

def test_unseen_schema_generalization():
    """
    Evaluates that ATLAS can ingest and profile completely arbitrary schemas
    without hardcoding column names or domain assumptions.
    """
    # Create an unfamiliar dataset: IoT sensor telemetry
    data = {
        "device_uuid": [f"dev_{i}" for i in range(100)],
        "timestamp_utc": pd.date_range("2026-01-01", periods=100, freq="h"),
        "temperature_c": np.random.normal(24.5, 2.0, 100),
        "pressure_kpa": np.random.normal(101.3, 0.5, 100),
        "status_code": np.random.choice(["OK", "WARN", "FAIL"], 100),
        "battery_pct": np.random.uniform(10.0, 100.0, 100)
    }
    df = pd.DataFrame(data)
    
    # 1. Infer schema
    schema = DatasetParser.infer_schema(df)
    assert schema["row_count"] == 100
    assert schema["column_count"] == 6
    assert "device_uuid" in schema["candidate_identifiers"]
    assert "timestamp_utc" in schema["candidate_dates"]

    # 2. Register with engine
    ds_id = "iot_telemetry_test"
    engine.register_dataset(ds_id, df)

    # 3. Execute general profiling tool
    env = registry.execute("profile_dataset", {}, dataset_id=ds_id)
    assert env.status == "success"
    assert "temperature_c" in env.result["columns"]
    assert env.result["columns"]["temperature_c"]["type_category"] == "numeric"
