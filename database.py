"""
CCIS Database — SQLite + SQLAlchemy models.
Tables: documents, chunks, obligations, requirements,
        relationships, risks, alerts, audit_log.
"""
import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Boolean,
    create_engine, event
)
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import DB_PATH

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Enable WAL mode for better concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Models ────────────────────────────────────────────────────────────────────

class DocumentModel(Base):
    __tablename__ = "documents"
    doc_id       = Column(String, primary_key=True)
    filename     = Column(String, nullable=False)
    doc_type     = Column(String, nullable=False)   # contract | policy
    parties      = Column(Text, default="[]")        # JSON list
    effective_date = Column(String, nullable=True)
    version      = Column(String, default="1.0")
    status       = Column(String, default="uploaded")  # uploaded|parsing|extracting|mapping|done|error
    error_msg    = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ChunkModel(Base):
    __tablename__ = "chunks"
    chunk_id        = Column(String, primary_key=True)
    doc_id          = Column(String, nullable=False, index=True)
    page            = Column(Integer, nullable=True)
    clause_id       = Column(String, nullable=True)
    parent_clause_id = Column(String, nullable=True)
    text            = Column(Text, nullable=False)
    char_start      = Column(Integer, nullable=True)
    char_end        = Column(Integer, nullable=True)
    token_count     = Column(Integer, nullable=True)
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ObligationModel(Base):
    __tablename__ = "obligations"
    obligation_id         = Column(String, primary_key=True)
    chunk_id              = Column(String, nullable=False, index=True)
    doc_id                = Column(String, nullable=False, index=True)
    statement             = Column(Text, nullable=False)
    responsible_party     = Column(Text, nullable=True)
    deadline              = Column(String, nullable=True)
    trigger_condition     = Column(Text, nullable=True)
    obligation_type       = Column(String, nullable=True)  # payment|reporting|security|deliverable|renewal|notice|...
    financial_exposure    = Column(Float, nullable=True)
    counterparty_tier     = Column(String, nullable=True)  # high|medium|low
    extraction_confidence = Column(Float, default=0.0)
    field_status          = Column(Text, default="{}")     # JSON dict
    source_evidence       = Column(Text, default="{}")     # JSON: doc_id, page, clause_id, text_span
    created_at            = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RequirementModel(Base):
    __tablename__ = "requirements"
    requirement_id        = Column(String, primary_key=True)
    chunk_id              = Column(String, nullable=False, index=True)
    doc_id                = Column(String, nullable=False, index=True)
    rule                  = Column(Text, nullable=False)
    scope                 = Column(Text, nullable=True)
    mandatory             = Column(Boolean, default=True)
    extraction_confidence = Column(Float, default=0.0)
    field_status          = Column(Text, default="{}")
    source_evidence       = Column(Text, default="{}")
    created_at            = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RelationshipModel(Base):
    __tablename__ = "relationships"
    relationship_id = Column(String, primary_key=True)
    obligation_id   = Column(String, nullable=False, index=True)
    requirement_id  = Column(String, nullable=False, index=True)
    edge_type       = Column(String, nullable=False)  # supports|conflicts|duplicates|unaddressed|policy_conflict
    confidence      = Column(Float, default=0.0)
    explanation     = Column(Text, nullable=True)
    evidence_a      = Column(Text, nullable=True)   # obligation text span
    evidence_b      = Column(Text, nullable=True)   # requirement text span
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RiskModel(Base):
    __tablename__ = "risks"
    risk_id              = Column(String, primary_key=True)
    obligation_id        = Column(String, nullable=True, index=True)
    requirement_id       = Column(String, nullable=True, index=True)
    relationship_id      = Column(String, nullable=True)
    doc_id               = Column(String, nullable=False, index=True)
    risk_type            = Column(String, nullable=False)  # deadline_breach|policy_conflict|missing_coverage|ambiguity|gap
    severity_score       = Column(Float, default=0.0)      # 1.0–10.0
    priority_band        = Column(String, default="Low")   # Critical|High|Medium|Low
    financial_exposure   = Column(Float, nullable=True)
    financial_source     = Column(String, default="estimated")  # extracted|estimated
    regulatory_severity  = Column(Float, default=5.0)
    deadline_urgency     = Column(Float, default=0.0)
    counterparty_importance = Column(Float, default=5.0)
    counterparty_source  = Column(String, default="estimated")
    explanation          = Column(Text, nullable=True)
    evidence_trail       = Column(Text, default="[]")      # JSON list of {chunk_id, text, source}
    llm_reasoning        = Column(Text, nullable=True)
    created_at           = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AlertModel(Base):
    __tablename__ = "alerts"
    alert_id        = Column(String, primary_key=True)
    risk_id         = Column(String, nullable=False, index=True)
    doc_id          = Column(String, nullable=False, index=True)
    owner_tag       = Column(String, nullable=True)   # legal|compliance|procurement
    priority_band   = Column(String, default="Low")
    message         = Column(Text, nullable=False)
    action_required = Column(Text, nullable=True)
    evidence_refs   = Column(Text, default="[]")      # JSON list of {label, doc_id, page, clause_id, text}
    acknowledged    = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLogModel(Base):
    __tablename__ = "audit_log"
    log_id           = Column(String, primary_key=True)
    doc_id           = Column(String, nullable=False, index=True)
    document_version = Column(String, default="1.0")
    stage            = Column(String, nullable=False)   # parse|extract|map|detect|prioritize|alert
    entity_id        = Column(String, nullable=True)    # chunk_id / obligation_id / risk_id / etc.
    input_hash       = Column(String, nullable=True)
    output_json      = Column(Text, nullable=True)
    model_reasoning  = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    import os
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    Base.metadata.create_all(bind=engine)
