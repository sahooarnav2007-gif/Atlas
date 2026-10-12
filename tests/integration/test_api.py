import pytest
import io
import json
from fastapi.testclient import TestClient
from backend.main import app
from examples.generate_sample_data import generate_sample_sales_data

client = TestClient(app)

def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_api_dataset_upload_and_get():
    df = generate_sample_sales_data(50, seed=77)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    
    files = {"file": ("test_sales.csv", io.BytesIO(csv_bytes), "text/csv")}
    data = {"dataset_family": "retail_ops", "version": "v1"}
    
    upload_res = client.post("/api/datasets", files=files, data=data)
    assert upload_res.status_code == 200
    ds_data = upload_res.json()
    ds_id = ds_data["dataset_id"]
    assert ds_data["row_count"] == 50

    # Retrieve dataset metadata
    get_res = client.get(f"/api/datasets/{ds_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["dataset_id"] == ds_id

def test_api_memory_lifecycle():
    # 1. Create
    create_res = client.post(
        "/api/memories",
        json={
            "type": "metric_definition",
            "key": "high_value_customer",
            "value": {"rule": "order_value > 500"},
            "dataset_family": "retail_ops"
        }
    )
    assert create_res.status_code == 200
    mem_data = create_res.json()
    mem_id = mem_data["memory_id"]

    # 2. List
    list_res = client.get("/api/memories?dataset_family=retail_ops")
    assert list_res.status_code == 200
    mems = list_res.json()
    assert any(m["memory_id"] == mem_id for m in mems)

    # 3. Delete
    del_res = client.delete(f"/api/memories/{mem_id}")
    assert del_res.status_code == 200
