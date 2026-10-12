import pytest
from atlas.analytics.engine import engine, AnalyticsEngineError
from atlas.ingestion.parser import DatasetParser, DatasetIngestionError
from atlas.tools.registry import registry

def test_sql_injection_defense():
    # Attempt harmful SQL operations
    harmful_queries = [
        "SELECT * FROM tbl_sales; DROP TABLE tbl_sales;",
        "DELETE FROM tbl_sales WHERE 1=1",
        "UPDATE tbl_sales SET revenue = 0",
        "SELECT * FROM read_csv('/etc/passwd')"
    ]
    for q in harmful_queries:
        with pytest.raises(AnalyticsEngineError):
            engine.execute_bounded_query(q)

def test_oversized_upload_rejection():
    # Simulate oversized file (> max_upload_mb)
    filename = "large_dataset.csv"
    oversized_bytes = (26 * 1024 * 1024)  # 26 MB, default limit is 25 MB
    with pytest.raises(DatasetIngestionError) as exc_info:
        DatasetParser.validate_file(filename, oversized_bytes)
    assert "exceeds maximum allowed limit" in str(exc_info.value)

def test_unsupported_file_extension_rejection():
    with pytest.raises(DatasetIngestionError):
        DatasetParser.validate_file("malicious_script.sh", 1024)

def test_invalid_query_parameters(registered_dataset):
    # Pass non-existent columns to tool
    envelope = registry.execute(
        "query_data",
        {"metrics": [{"column": "non_existent_column_123", "aggregation": "sum"}]},
        dataset_id=registered_dataset
    )
    assert envelope.status == "error"
    assert "error_message" in envelope.model_dump()
