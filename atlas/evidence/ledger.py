import uuid
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ToolExecutionEnvelope(BaseModel):
    operation_id: str = Field(default_factory=lambda: f"op_{uuid.uuid4().hex[:8]}")
    tool_name: str
    status: str = "success"  # "success" or "error"
    dataset_id: str
    dataset_version: str = "v1"
    validated_parameters: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    duration_ms: int = 0
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ProvenanceRecord(BaseModel):
    operation_id: str
    tool_name: str
    dataset_id: str
    dataset_version: str
    parameter_hash: str
    timestamp: str
    duration_ms: int
    assumptions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class EvidenceLedger:
    def __init__(self):
        self._envelopes: List[ToolExecutionEnvelope] = []
        self._provenance_entries: List[ProvenanceRecord] = []

    def record_execution(
        self,
        envelope: ToolExecutionEnvelope,
        assumptions: Optional[List[str]] = None
    ) -> None:
        self._envelopes.append(envelope)
        param_str = json.dumps(envelope.validated_parameters, sort_keys=True, default=str)
        param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        
        record = ProvenanceRecord(
            operation_id=envelope.operation_id,
            tool_name=envelope.tool_name,
            dataset_id=envelope.dataset_id,
            dataset_version=envelope.dataset_version,
            parameter_hash=param_hash,
            timestamp=envelope.created_at,
            duration_ms=envelope.duration_ms,
            assumptions=assumptions or [],
            warnings=envelope.warnings
        )
        self._provenance_entries.append(record)

    def get_envelopes(self) -> List[Dict[str, Any]]:
        return [env.model_dump() for env in self._envelopes]

    def get_provenance_summary(self) -> List[Dict[str, Any]]:
        return [prov.model_dump() for env in self._provenance_entries]

    def clear(self):
        self._envelopes.clear()
        self._provenance_entries.clear()
