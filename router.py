"""
CCIS Risk Router — risk query endpoints.

GET /api/risks — paginated, filterable by severity/doc.
GET /api/risks/{risk_id} — full detail with evidence trail.
GET /api/obligations — list all obligations with source evidence.
GET /api/requirements — list all requirements with source evidence.
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db, RiskModel, ObligationModel, RequirementModel, RelationshipModel

router = APIRouter()


@router.get("/risks")
def list_risks(
    doc_id: Optional[str] = None,
    priority_band: Optional[str] = None,
    risk_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(1000, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """List risks with filtering and pagination."""
    query = db.query(RiskModel)

    if doc_id:
        query = query.filter(RiskModel.doc_id == doc_id)
    if priority_band:
        query = query.filter(RiskModel.priority_band == priority_band)
    if risk_type:
        query = query.filter(RiskModel.risk_type == risk_type)

    total = query.count()
    risks = query.order_by(
        RiskModel.severity_score.desc()
    ).offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "risks": [_risk_to_dict(r) for r in risks],
    }


@router.get("/risks/{risk_id}")
def get_risk_detail(risk_id: str, db: Session = Depends(get_db)):
    """Get full risk detail with evidence trail."""
    risk = db.query(RiskModel).filter(RiskModel.risk_id == risk_id).first()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk not found")

    result = _risk_to_dict(risk)

    # Enrich with linked obligation
    if risk.obligation_id:
        obl = db.query(ObligationModel).filter(
            ObligationModel.obligation_id == risk.obligation_id
        ).first()
        if obl:
            result["obligation"] = _obligation_to_dict(obl)

    # Enrich with linked requirement
    if risk.requirement_id:
        req = db.query(RequirementModel).filter(
            RequirementModel.requirement_id == risk.requirement_id
        ).first()
        if req:
            result["requirement"] = _requirement_to_dict(req)

    # Enrich with relationship
    if risk.relationship_id:
        rel = db.query(RelationshipModel).filter(
            RelationshipModel.relationship_id == risk.relationship_id
        ).first()
        if rel:
            result["relationship"] = {
                "relationship_id": rel.relationship_id,
                "edge_type": rel.edge_type,
                "confidence": rel.confidence,
                "explanation": rel.explanation,
                "evidence_a": rel.evidence_a,
                "evidence_b": rel.evidence_b,
            }

    return result


@router.get("/obligations")
def list_obligations(
    doc_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(ObligationModel)
    if doc_id:
        query = query.filter(ObligationModel.doc_id == doc_id)
    return [_obligation_to_dict(o) for o in query.all()]


@router.get("/requirements")
def list_requirements(
    doc_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(RequirementModel)
    if doc_id:
        query = query.filter(RequirementModel.doc_id == doc_id)
    return [_requirement_to_dict(r) for r in query.all()]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _risk_to_dict(r: RiskModel) -> dict:
    return {
        "risk_id": r.risk_id,
        "obligation_id": r.obligation_id,
        "requirement_id": r.requirement_id,
        "relationship_id": r.relationship_id,
        "doc_id": r.doc_id,
        "risk_type": r.risk_type,
        "severity_score": r.severity_score,
        "priority_band": r.priority_band,
        "financial_exposure": r.financial_exposure,
        "financial_source": r.financial_source,
        "regulatory_severity": r.regulatory_severity,
        "deadline_urgency": r.deadline_urgency,
        "counterparty_importance": r.counterparty_importance,
        "counterparty_source": r.counterparty_source,
        "explanation": r.explanation,
        "evidence_trail": json.loads(r.evidence_trail) if r.evidence_trail else [],
        "llm_reasoning": r.llm_reasoning,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _obligation_to_dict(o: ObligationModel) -> dict:
    return {
        "obligation_id": o.obligation_id,
        "chunk_id": o.chunk_id,
        "doc_id": o.doc_id,
        "statement": o.statement,
        "responsible_party": o.responsible_party,
        "deadline": o.deadline,
        "trigger_condition": o.trigger_condition,
        "obligation_type": o.obligation_type,
        "financial_exposure": o.financial_exposure,
        "counterparty_tier": o.counterparty_tier,
        "extraction_confidence": o.extraction_confidence,
        "field_status": json.loads(o.field_status) if o.field_status else {},
        "source_evidence": json.loads(o.source_evidence) if o.source_evidence else {},
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


def _requirement_to_dict(r: RequirementModel) -> dict:
    return {
        "requirement_id": r.requirement_id,
        "chunk_id": r.chunk_id,
        "doc_id": r.doc_id,
        "rule": r.rule,
        "scope": r.scope,
        "mandatory": r.mandatory,
        "extraction_confidence": r.extraction_confidence,
        "field_status": json.loads(r.field_status) if r.field_status else {},
        "source_evidence": json.loads(r.source_evidence) if r.source_evidence else {},
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
