from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from backend.schemas.models import MemoryCreateRequest, MemoryUpdateRequest
from atlas.memory.service import memory_service
from atlas.persistence.db import get_db

router = APIRouter(prefix="/api/memories", tags=["memories"])

@router.get("")
def list_memories(
    dataset_family: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return memory_service.retrieve_memories(
        dataset_family=dataset_family,
        memory_type=memory_type,
        db_session=db
    )

@router.post("")
def create_memory(req: MemoryCreateRequest, db: Session = Depends(get_db)):
    mem = memory_service.save_memory(
        memory_type=req.type,
        key=req.key,
        value=req.value,
        dataset_family=req.dataset_family or "default",
        columns=req.columns or [],
        source=req.source or "explicit_user",
        confidence=req.confidence or 1.0,
        db_session=db
    )
    return mem

@router.patch("/{memory_id}")
def update_memory(memory_id: str, req: MemoryUpdateRequest, db: Session = Depends(get_db)):
    updated = memory_service.update_memory(
        memory_id=memory_id,
        value=req.value,
        status=req.status,
        db_session=db
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found.")
    return updated

@router.delete("/{memory_id}")
def delete_memory(memory_id: str, db: Session = Depends(get_db)):
    success = memory_service.delete_memory(memory_id, db_session=db)
    if not success:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found.")
    return {"status": "deleted", "memory_id": memory_id}
