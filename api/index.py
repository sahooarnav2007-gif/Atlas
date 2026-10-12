import csv
import io
import json
import math
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="ATLAS - Agentic Tabular Intelligence (Vercel API)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for serverless execution (seeded with demo dataset)
DATASETS: Dict[str, List[Dict[str, Any]]] = {}
MEMORIES: List[Dict[str, Any]] = [
    {
        "memory_id": "mem_default_01",
        "type": "metric_definition",
        "dataset_family": "retail_orders",
        "columns": ["order_status"],
        "key": "active_orders_only",
        "value": {
            "definition": "Exclude Cancelled orders when calculating active net revenue if requested",
            "rule": "order_status != 'Cancelled'"
        },
        "source": "explicit_user",
        "confidence": 1.0,
        "version": 1,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
]

def _load_demo_rows() -> List[Dict[str, Any]]:
    if "ds_retail_demo" in DATASETS:
        return DATASETS["ds_retail_demo"]
    candidates = [
        Path(__file__).parent.parent / "data" / "demo_retail_orders.csv",
        Path(__file__).parent.parent / "public" / "demo_retail_orders.csv",
        Path("data/demo_retail_orders.csv"),
        Path("public/demo_retail_orders.csv"),
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = []
                for r in reader:
                    clean = {}
                    for k, v in r.items():
                        if v is None or v == "":
                            clean[k] = None
                        else:
                            try:
                                if "." in v:
                                    clean[k] = float(v)
                                else:
                                    clean[k] = int(v)
                            except ValueError:
                                clean[k] = v
                    rows.append(clean)
                DATASETS["ds_retail_demo"] = rows
                return rows
    return []

class AnalysisPayload(BaseModel):
    dataset_id: str = "ds_retail_demo"
    question: str
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MemoryCreatePayload(BaseModel):
    type: str = "metric_definition"
    key: str
    value: Dict[str, Any]
    dataset_family: str = "retail_orders"
    columns: List[str] = Field(default_factory=list)

@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "healthy", "platform": "vercel", "version": "0.1.0"}

@app.post("/api/datasets/demo")
def load_demo():
    rows = _load_demo_rows()
    cols = list(rows[0].keys()) if rows else []
    return {
        "dataset_id": "ds_retail_demo",
        "filename": "demo_retail_orders.csv",
        "dataset_family": "retail_orders",
        "version": "v1",
        "row_count": len(rows),
        "column_count": len(cols),
        "columns": cols,
        "rows": rows
    }

@app.get("/api/memories")
def list_memories():
    return [m for m in MEMORIES if m.get("status") == "active"]

@app.post("/api/memories")
def add_memory(payload: MemoryCreatePayload):
    version = 1
    for m in MEMORIES:
        if m["key"] == payload.key and m["status"] == "active":
            m["status"] = "superseded"
            version = m["version"] + 1
    new_mem = {
        "memory_id": f"mem_{uuid.uuid4().hex[:8]}",
        "type": payload.type,
        "dataset_family": payload.dataset_family,
        "columns": payload.columns,
        "key": payload.key,
        "value": payload.value,
        "source": "explicit_user",
        "confidence": 1.0,
        "version": version,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    MEMORIES.append(new_mem)
    return new_mem

@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: str):
    for m in MEMORIES:
        if m["memory_id"] == memory_id:
            m["status"] = "deleted"
            return {"status": "deleted", "memory_id": memory_id}
    raise HTTPException(status_code=404, detail="Memory not found")

@app.post("/api/analyses")
def analyze(payload: AnalysisPayload):
    start = time.time()
    rows = _load_demo_rows() if payload.dataset_id == "ds_retail_demo" else DATASETS.get(payload.dataset_id, _load_demo_rows())
    if not rows:
        raise HTTPException(status_code=400, detail="Dataset empty or not found")

    q = payload.question.lower()
    cols = list(rows[0].keys())
    num_cols = [c for c in cols if any(isinstance(r.get(c), (int, float)) for r in rows[:20])]
    cat_cols = [c for c in cols if c not in num_cols]

    dim = next((c for c in cat_cols if c.lower().replace("_", " ") in q or c.lower() in q), "region" if "region" in cat_cols else cat_cols[0])
    metric = next((c for c in num_cols if c.lower().replace("_", " ") in q or c.lower() in q), "revenue_inr" if "revenue_inr" in num_cols else num_cols[0])

    totals: Dict[str, float] = {}
    for r in rows:
        k = str(r.get(dim) or "Unknown")
        v = r.get(metric)
        if isinstance(v, (int, float)):
            totals[k] = totals.get(k, 0.0) + float(v)

    sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
    result_rows = [{dim: k, metric: round(v, 2)} for k, v in sorted_items]
    duration_ms = max(1, int((time.time() - start) * 1000))
    op_id = f"op_{uuid.uuid4().hex[:8]}"

    top_str = ", ".join(f"{item[dim]} ({item[metric]:,.2f})" for item in result_rows[:3])
    answer = f"I've created a bar chart for \"{metric} by {dim}\". Check the Dashboard! Top contributors: {top_str}."

    return {
        "analysis_id": f"an_{uuid.uuid4().hex[:8]}",
        "dataset_id": payload.dataset_id,
        "status": "completed",
        "question": payload.question,
        "answer": answer,
        "chart": {
            "title": f"{metric.replace('_', ' ').title()} by {dim.replace('_', ' ').title()}",
            "x_col": dim,
            "y_col": metric,
            "x": [r[dim] for r in result_rows],
            "y": [r[metric] for r in result_rows],
            "badge": f"{len(result_rows)} pts"
        },
        "execution_trace": [
            {
                "operation_id": op_id,
                "tool_name": "query_data",
                "status": "success",
                "dataset_id": payload.dataset_id,
                "dataset_version": "v1",
                "validated_parameters": {"group_by": [dim], "metric": metric, "aggregation": "sum", "limit": 10},
                "result": {"columns": [dim, metric], "rows": result_rows},
                "warnings": [],
                "duration_ms": duration_ms
            }
        ],
        "duration_ms": duration_ms
    }
