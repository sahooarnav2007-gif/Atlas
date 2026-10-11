import os
import uuid
import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from atlas.config import settings
from atlas.ingestion.parser import DatasetParser, DatasetIngestionError
from atlas.analytics.engine import engine
from atlas.persistence.db import get_db, DatasetRecord

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

@router.post("/demo")
def load_demo_dataset(db: Session = Depends(get_db)):
    demo_file = Path("data/demo_retail_orders.csv")
    if not demo_file.exists():
        raise HTTPException(status_code=404, detail="Demo dataset file not found.")

    dataset_id = "ds_retail_demo"
    df, warnings = DatasetParser.load_dataframe(str(demo_file))
    schema_info = DatasetParser.infer_schema(df)
    engine.register_dataset(dataset_id, df)

    record = db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id).first()
    if not record:
        record = DatasetRecord(
            dataset_id=dataset_id,
            filename="demo_retail_orders.csv",
            file_path=str(demo_file),
            file_size_bytes=demo_file.stat().st_size,
            row_count=schema_info["row_count"],
            column_count=schema_info["column_count"],
            version="v1",
            dataset_family="retail_orders",
            schema_info=json.dumps(schema_info),
            warnings=json.dumps(warnings)
        )
        db.add(record)
    else:
        record.schema_info = json.dumps(schema_info)
        record.row_count = schema_info["row_count"]
        record.column_count = schema_info["column_count"]
    db.commit()

    return {
        "dataset_id": dataset_id,
        "filename": "demo_retail_orders.csv",
        "dataset_family": "retail_orders",
        "version": "v1",
        "row_count": schema_info["row_count"],
        "column_count": schema_info["column_count"],
        "schema": schema_info,
        "warnings": warnings
    }

@router.post("")
async def upload_dataset(
    file: UploadFile = File(...),
    dataset_family: str = Form(default="default"),
    version: str = Form(default="v1"),
    db: Session = Depends(get_db)
):
    # Validate file size & extension
    contents = await file.read()
    file_size = len(contents)
    filename = file.filename or "dataset.csv"

    try:
        DatasetParser.validate_file(filename, file_size)
    except DatasetIngestionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    dataset_id = f"ds_{uuid.uuid4().hex[:8]}"
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = settings.upload_dir / f"{dataset_id}_{filename}"

    with open(file_path, "wb") as f:
        f.write(contents)

    try:
        df, warnings = DatasetParser.load_dataframe(str(file_path))
        schema_info = DatasetParser.infer_schema(df)
    except DatasetIngestionError as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))

    # Register into DuckDB Analytics Engine
    engine.register_dataset(dataset_id, df)

    # Persist record
    record = DatasetRecord(
        dataset_id=dataset_id,
        filename=filename,
        file_path=str(file_path),
        file_size_bytes=file_size,
        row_count=schema_info["row_count"],
        column_count=schema_info["column_count"],
        version=version,
        dataset_family=dataset_family,
        schema_info=json.dumps(schema_info),
        warnings=json.dumps(warnings)
    )
    db.add(record)
    db.commit()

    return {
        "dataset_id": dataset_id,
        "filename": filename,
        "dataset_family": dataset_family,
        "version": version,
        "row_count": schema_info["row_count"],
        "column_count": schema_info["column_count"],
        "schema": schema_info,
        "warnings": warnings
    }

@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    record = db.query(DatasetRecord).filter(DatasetRecord.dataset_id == dataset_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found.")

    return {
        "dataset_id": record.dataset_id,
        "filename": record.filename,
        "dataset_family": record.dataset_family,
        "version": record.version,
        "row_count": record.row_count,
        "column_count": record.column_count,
        "schema": json.loads(record.schema_info),
        "warnings": json.loads(record.warnings),
        "created_at": record.created_at.isoformat() if record.created_at else None
    }
