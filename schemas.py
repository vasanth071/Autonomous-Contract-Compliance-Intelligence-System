"""
CCIS Pydantic Schemas — canonical data shapes for all pipeline objects.

Key design choices (from spec):
- extraction_confidence: float on every extracted object
- field_status: maps each optional field to "present" | "absent_in_source" | "extraction_uncertain"
- source_evidence: always includes doc_id, page, clause_id, and the exact raw text span
- Risk scoring inputs are tagged as "extracted" or "estimated"
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ── Source Evidence (attached to every extracted object) ─────────────────────

class SourceEvidence(BaseModel):
    doc_id: str
    page: Optional[int] = None
    clause_id: Optional[str] = None
    text_span: str = Field(..., description="Exact raw text from source — never paraphrased")


# ── Document ──────────────────────────────────────────────────────────────────

class DocumentCreate(BaseModel):
    filename: str
    doc_type: Literal["contract", "policy"]
    parties: List[str] = []
    effective_date: Optional[str] = None
    version: str = "1.0"

class DocumentSchema(DocumentCreate):
    doc_id: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True


# ── Chunk ─────────────────────────────────────────────────────────────────────

class ChunkSchema(BaseModel):
    chunk_id: str
    doc_id: str
    page: Optional[int] = None
    clause_id: Optional[str] = None
    parent_clause_id: Optional[str] = None
    text: str
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    token_count: Optional[int] = None
    class Config:
        from_attributes = True


# ── Obligation Object ─────────────────────────────────────────────────────────

class ObligationSchema(BaseModel):
    obligation_id: str
    chunk_id: str
    doc_id: str
    statement: str = Field(..., description="What must be done")
    responsible_party: Optional[str] = None
    deadline: Optional[str] = None
    trigger_condition: Optional[str] = None
    obligation_type: Optional[str] = None  # payment|reporting|security|deliverable|renewal|notice|...
    financial_exposure: Optional[float] = None
    counterparty_tier: Optional[str] = None  # high|medium|low
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    field_status: Dict[str, Literal["present", "absent_in_source", "extraction_uncertain"]] = {}
    source_evidence: SourceEvidence
    created_at: datetime
    class Config:
        from_attributes = True


# ── Requirement Object ────────────────────────────────────────────────────────

class RequirementSchema(BaseModel):
    requirement_id: str
    chunk_id: str
    doc_id: str
    rule: str = Field(..., description="The policy/regulatory rule")
    scope: Optional[str] = None
    mandatory: bool = True
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    field_status: Dict[str, Literal["present", "absent_in_source", "extraction_uncertain"]] = {}
    source_evidence: SourceEvidence
    created_at: datetime
    class Config:
        from_attributes = True


# ── Relationship (graph edge) ─────────────────────────────────────────────────

class RelationshipSchema(BaseModel):
    relationship_id: str
    obligation_id: str
    requirement_id: str
    edge_type: Literal["supports", "conflicts", "duplicates", "unaddressed", "policy_conflict"]
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: Optional[str] = None
    evidence_a: Optional[str] = None   # obligation text
    evidence_b: Optional[str] = None   # requirement text
    created_at: datetime
    class Config:
        from_attributes = True


# ── Evidence Trail entry ──────────────────────────────────────────────────────

class EvidenceEntry(BaseModel):
    label: str
    doc_id: str
    page: Optional[int] = None
    clause_id: Optional[str] = None
    text: str


# ── Risk Object ───────────────────────────────────────────────────────────────

class RiskSchema(BaseModel):
    risk_id: str
    obligation_id: Optional[str] = None
    requirement_id: Optional[str] = None
    relationship_id: Optional[str] = None
    doc_id: str
    risk_type: Literal["deadline_breach", "policy_conflict", "missing_coverage", "ambiguity", "gap"]
    severity_score: float = Field(ge=0.0, le=10.0)
    priority_band: Literal["Critical", "High", "Medium", "Low"]
    financial_exposure: Optional[float] = None
    financial_source: Literal["extracted", "estimated"] = "estimated"
    regulatory_severity: float = 5.0
    deadline_urgency: float = 0.0
    counterparty_importance: float = 5.0
    counterparty_source: Literal["extracted", "estimated"] = "estimated"
    explanation: Optional[str] = None
    evidence_trail: List[EvidenceEntry] = []
    llm_reasoning: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True


# ── Alert Object ──────────────────────────────────────────────────────────────

class AlertSchema(BaseModel):
    alert_id: str
    risk_id: str
    doc_id: str
    owner_tag: Optional[str] = None   # legal|compliance|procurement
    priority_band: Literal["Critical", "High", "Medium", "Low"]
    message: str
    action_required: Optional[str] = None
    evidence_refs: List[EvidenceEntry] = []
    acknowledged: bool = False
    created_at: datetime
    class Config:
        from_attributes = True


# ── Audit Log Entry ───────────────────────────────────────────────────────────

class AuditEntrySchema(BaseModel):
    log_id: str
    doc_id: str
    document_version: str
    stage: str
    entity_id: Optional[str] = None
    input_hash: Optional[str] = None
    output_json: Optional[str] = None
    model_reasoning: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True


# ── Pipeline status response ──────────────────────────────────────────────────

class PipelineStatusResponse(BaseModel):
    doc_id: str
    status: str
    message: str


# ── Graph ─────────────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    node_type: Literal["obligation", "requirement"]
    doc_id: str

class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: str
    confidence: float
    explanation: Optional[str] = None

class GraphSchema(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
