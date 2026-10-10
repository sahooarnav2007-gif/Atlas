import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Text, Boolean, DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from atlas.config import settings

Base = declarative_base()

class DatasetRecord(Base):
    __tablename__ = "datasets"

    dataset_id = Column(String(64), primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    row_count = Column(Integer, nullable=False)
    column_count = Column(Integer, nullable=False)
    version = Column(String(32), default="v1")
    dataset_family = Column(String(128), default="default")
    schema_info = Column(Text, nullable=False)  # JSON string
    warnings = Column(Text, default="[]")  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

class MemoryRecord(Base):
    __tablename__ = "memories"

    memory_id = Column(String(64), primary_key=True)
    type = Column(String(64), nullable=False)  # metric_definition, column_semantics, preference, reusable_filter
    dataset_family = Column(String(128), default="default")
    columns = Column(Text, default="[]")  # JSON list
    key = Column(String(128), nullable=False)
    value = Column(Text, nullable=False)  # JSON dictionary with definition, rule, etc.
    source = Column(String(64), default="explicit_user")  # explicit_user, agent_inference
    confidence = Column(Float, default=1.0)
    version = Column(Integer, default=1)
    status = Column(String(32), default="active")  # active, superseded, deleted
    superseded_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AnalysisRecord(Base):
    __tablename__ = "analyses"

    analysis_id = Column(String(64), primary_key=True)
    dataset_id = Column(String(64), nullable=False)
    question = Column(Text, nullable=False)
    status = Column(String(32), default="pending")  # pending, running, completed, failed
    plan = Column(Text, nullable=True)  # JSON array
    evidence_backed_response = Column(Text, nullable=True)  # JSON response or Markdown
    tool_trace = Column(Text, default="[]")  # JSON array of tool execution envelopes
    provenance = Column(Text, default="{}")  # JSON provenance metadata
    warnings = Column(Text, default="[]")  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

# Configure database engine
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionFactory = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()
