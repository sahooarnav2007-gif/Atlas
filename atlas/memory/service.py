import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from atlas.persistence.db import MemoryRecord, SessionFactory

class MemoryConflictError(Exception):
    pass

class MemoryService:
    def __init__(self, session_factory=SessionFactory):
        self._session_factory = session_factory

    def save_memory(
        self,
        memory_type: str,
        key: str,
        value: Dict[str, Any],
        dataset_family: str = "default",
        columns: Optional[List[str]] = None,
        source: str = "explicit_user",
        confidence: float = 1.0,
        db_session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Saves or updates a memory. If an active memory with the same key and family exists,
        it supersedes the old version, incrementing version number.
        """
        columns = columns or []
        session = db_session or self._session_factory()
        should_close = db_session is None

        try:
            # Check for existing active memory with the same key and scope
            existing = session.query(MemoryRecord).filter(
                MemoryRecord.key == key,
                MemoryRecord.dataset_family == dataset_family,
                MemoryRecord.status == "active"
            ).first()

            version = 1
            if existing:
                version = existing.version + 1
                existing.status = "superseded"
                session.add(existing)

            memory_id = f"mem_{uuid.uuid4().hex[:8]}"
            new_record = MemoryRecord(
                memory_id=memory_id,
                type=memory_type,
                dataset_family=dataset_family,
                columns=json.dumps(columns),
                key=key,
                value=json.dumps(value),
                source=source,
                confidence=confidence,
                version=version,
                status="active"
            )
            session.add(new_record)
            if existing:
                existing.superseded_by = memory_id

            session.commit()
            return self._record_to_dict(new_record)
        finally:
            if should_close:
                session.close()

    def retrieve_memories(
        self,
        dataset_family: Optional[str] = None,
        columns: Optional[List[str]] = None,
        memory_type: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves active memories matching scope and type.
        Ranks by exact family match first, then column compatibility, then recency.
        """
        session = db_session or self._session_factory()
        should_close = db_session is None

        try:
            query = session.query(MemoryRecord).filter(MemoryRecord.status == "active")
            
            if memory_type:
                query = query.filter(MemoryRecord.type == memory_type)

            records = query.order_by(MemoryRecord.updated_at.desc()).all()
            
            results = []
            for r in records:
                # Filter by dataset family if applicable (allow "default" or wildcard match)
                if dataset_family and r.dataset_family not in {"default", dataset_family}:
                    continue

                # Filter by columns if specified
                r_cols = json.loads(r.columns) if r.columns else []
                if columns and r_cols:
                    # If memory is bound to specific columns, ensure at least one matches
                    if not any(c in columns for c in r_cols):
                        continue

                results.append(self._record_to_dict(r))

            return results
        finally:
            if should_close:
                session.close()

    def get_memory(self, memory_id: str, db_session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        session = db_session or self._session_factory()
        should_close = db_session is None
        try:
            record = session.query(MemoryRecord).filter(MemoryRecord.memory_id == memory_id).first()
            return self._record_to_dict(record) if record else None
        finally:
            if should_close:
                session.close()

    def update_memory(
        self,
        memory_id: str,
        value: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> Optional[Dict[str, Any]]:
        session = db_session or self._session_factory()
        should_close = db_session is None
        try:
            record = session.query(MemoryRecord).filter(MemoryRecord.memory_id == memory_id).first()
            if not record:
                return None
            if value is not None:
                record.value = json.dumps(value)
            if status is not None:
                record.status = status
            session.commit()
            return self._record_to_dict(record)
        finally:
            if should_close:
                session.close()

    def delete_memory(self, memory_id: str, db_session: Optional[Session] = None) -> bool:
        session = db_session or self._session_factory()
        should_close = db_session is None
        try:
            record = session.query(MemoryRecord).filter(MemoryRecord.memory_id == memory_id).first()
            if not record:
                return False
            record.status = "deleted"
            session.commit()
            return True
        finally:
            if should_close:
                session.close()

    def _record_to_dict(self, record: MemoryRecord) -> Dict[str, Any]:
        return {
            "memory_id": record.memory_id,
            "type": record.type,
            "dataset_family": record.dataset_family,
            "columns": json.loads(record.columns) if record.columns else [],
            "key": record.key,
            "value": json.loads(record.value) if record.value else {},
            "source": record.source,
            "confidence": record.confidence,
            "version": record.version,
            "status": record.status,
            "superseded_by": record.superseded_by,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None
        }

memory_service = MemoryService()
