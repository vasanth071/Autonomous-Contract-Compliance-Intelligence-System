"""
CCIS Audit Logger — logs every pipeline step to audit_log table.

Includes document_version for diffable trails when re-processing amended documents.
"""
import uuid
import json
import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.database import AuditLogModel, DocumentModel


def log_audit(
    db: Session,
    doc_id: str,
    stage: str,
    entity_id: str = None,
    input_data: str = None,
    output: str = None,
    reasoning: str = None,
):
    """Write a single audit log entry."""
    # Look up document version
    doc = db.query(DocumentModel).filter(DocumentModel.doc_id == doc_id).first()
    doc_version = doc.version if doc else "1.0"

    input_hash = None
    if input_data:
        input_hash = hashlib.sha256(input_data.encode()).hexdigest()[:16]

    entry = AuditLogModel(
        log_id=str(uuid.uuid4()),
        doc_id=doc_id,
        document_version=doc_version,
        stage=stage,
        entity_id=entity_id,
        input_hash=input_hash,
        output_json=output,
        model_reasoning=reasoning,
    )
    db.add(entry)
    db.commit()
