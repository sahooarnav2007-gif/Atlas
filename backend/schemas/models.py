from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AnalysisRequest(BaseModel):
    dataset_id: str
    question: str
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MemoryCreateRequest(BaseModel):
    type: str  # metric_definition, column_semantics, preference, reusable_filter
    key: str
    value: Dict[str, Any]
    dataset_family: Optional[str] = "default"
    columns: Optional[List[str]] = Field(default_factory=list)
    source: Optional[str] = "explicit_user"
    confidence: Optional[float] = 1.0

class MemoryUpdateRequest(BaseModel):
    value: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
