import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.schemas.models import AnalysisRequest
from atlas.agent.orchestrator import orchestrator
from atlas.persistence.db import get_db, AnalysisRecord

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

@router.post("")
def submit_analysis(req: AnalysisRequest):
    result = orchestrator.run_analysis(
        dataset_id=req.dataset_id,
        question=req.question,
        options=req.options
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result.get("error", "Analysis execution failed."))
    return result

@router.get("/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db)):
    record = db.query(AnalysisRecord).filter(AnalysisRecord.analysis_id == analysis_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found.")

    return {
        "analysis_id": record.analysis_id,
        "dataset_id": record.dataset_id,
        "question": record.question,
        "status": record.status,
        "plan": json.loads(record.plan) if record.plan else [],
        "response": record.evidence_backed_response,
        "tool_trace": json.loads(record.tool_trace) if record.tool_trace else [],
        "warnings": json.loads(record.warnings) if record.warnings else [],
        "created_at": record.created_at.isoformat() if record.created_at else None
    }
