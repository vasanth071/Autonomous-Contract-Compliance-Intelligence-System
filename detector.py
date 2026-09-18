"""
CCIS Risk Detection — hybrid rule-based + LLM risk detector.

Reviews ALL edge types (conflicts, duplicates, unaddressed, policy_conflict).
Rule engine checks deadlines, missing fields, conflict edges.
LLM pass confirms conflicts and assesses severity.
"""
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict

from anthropic import Anthropic

from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, DEADLINE_WARN_DAYS
from backend.database import (
    SessionLocal, ObligationModel, RequirementModel, RelationshipModel,
    RiskModel, AuditLogModel
)
from backend.extraction.prompts import (
    SYSTEM_PROMPT, RISK_CONFIRMATION_PROMPT, RISK_ASSESSMENT_TOOL
)

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_anthropic_api_key_here" else None


def detect_risks(doc_id: str) -> List[Dict]:
    """Detect all risks for obligations in a document."""
    db = SessionLocal()
    risks: List[Dict] = []

    try:
        obligations = db.query(ObligationModel).filter(
            ObligationModel.doc_id == doc_id
        ).all()
        relationships = db.query(RelationshipModel).filter(
            RelationshipModel.obligation_id.in_(
                [o.obligation_id for o in obligations]
            )
        ).all() if obligations else []

        # ── PASS 1: Rule-based checks ────────────────────────────────────
        for obl in obligations:
            field_status = json.loads(obl.field_status) if obl.field_status else {}
            source_ev = json.loads(obl.source_evidence) if obl.source_evidence else {}

            # Deadline breach check
            if obl.deadline:
                deadline_risk = _check_deadline(obl.deadline)
                if deadline_risk:
                    risk = _create_risk(
                        db, doc_id, obl, None, None,
                        "deadline_breach", deadline_risk["severity"],
                        deadline_risk["explanation"],
                        [{"label": "Obligation clause",
                          "doc_id": doc_id,
                          "page": source_ev.get("page"),
                          "clause_id": source_ev.get("clause_id"),
                          "text": source_ev.get("text_span", obl.statement[:300])}]
                    )
                    risks.append(risk)

            # Missing responsible party check
            if field_status.get("responsible_party") == "absent_in_source":
                if obl.obligation_type in ("payment", "deliverable", "reporting", "notice", "compliance"):
                    risk = _create_risk(
                        db, doc_id, obl, None, None,
                        "ambiguity", 5.0,
                        f"Action-requiring obligation of type '{obl.obligation_type}' has no assigned responsible party. "
                        f"Field marked as absent_in_source during extraction.",
                        [{"label": "Obligation without responsible party",
                          "doc_id": doc_id,
                          "page": source_ev.get("page"),
                          "clause_id": source_ev.get("clause_id"),
                          "text": source_ev.get("text_span", obl.statement[:300])}]
                    )
                    risks.append(risk)

        # ── PASS 1b: Relationship-based rule checks ──────────────────────
        for rel in relationships:
            if rel.edge_type in ("conflicts", "policy_conflict"):
                obl = db.query(ObligationModel).filter(
                    ObligationModel.obligation_id == rel.obligation_id
                ).first()
                req = db.query(RequirementModel).filter(
                    RequirementModel.requirement_id == rel.requirement_id
                ).first()

                if not obl or not req:
                    continue

                obl_ev = json.loads(obl.source_evidence) if obl.source_evidence else {}
                req_ev = json.loads(req.source_evidence) if req.source_evidence else {}

                evidence_trail = [
                    {"label": "Contract obligation",
                     "doc_id": obl.doc_id,
                     "page": obl_ev.get("page"),
                     "clause_id": obl_ev.get("clause_id"),
                     "text": obl_ev.get("text_span", obl.statement[:300])},
                    {"label": "Policy requirement",
                     "doc_id": req.doc_id,
                     "page": req_ev.get("page"),
                     "clause_id": req_ev.get("clause_id"),
                     "text": req_ev.get("text_span", req.rule[:300])},
                ]

                # ── PASS 2: LLM severity assessment ──────────────────────
                llm_result = _llm_assess_risk(
                    rel.edge_type, rel.explanation or "",
                    obl.statement, obl.doc_id,
                    req.rule, req.doc_id,
                )

                severity = llm_result.get("severity_score", 7.0) if llm_result else 7.0
                explanation = llm_result.get("risk_explanation", rel.explanation or "Policy conflict detected") if llm_result else (rel.explanation or "Policy conflict detected")
                reasoning = llm_result.get("recommended_action", "") if llm_result else ""

                risk = _create_risk(
                    db, doc_id, obl, req, rel,
                    "policy_conflict", severity,
                    explanation, evidence_trail,
                    llm_reasoning=f"LLM assessment: {reasoning}",
                )
                risks.append(risk)

        # ── Check for unaddressed obligations (coverage gaps) ─────────────
        for obl in obligations:
            has_relationship = any(
                r.obligation_id == obl.obligation_id and r.edge_type != "unaddressed"
                for r in relationships
            )
            if not has_relationship and obl.obligation_type in ("compliance", "security", "reporting"):
                source_ev = json.loads(obl.source_evidence) if obl.source_evidence else {}
                risk = _create_risk(
                    db, doc_id, obl, None, None,
                    "gap", 4.0,
                    f"Obligation of type '{obl.obligation_type}' has no matching policy requirement. "
                    f"This may indicate a compliance coverage gap.",
                    [{"label": "Unmatched obligation",
                      "doc_id": doc_id,
                      "page": source_ev.get("page"),
                      "clause_id": source_ev.get("clause_id"),
                      "text": source_ev.get("text_span", obl.statement[:300])}]
                )
                risks.append(risk)

        db.commit()
    finally:
        db.close()

    return risks


def _check_deadline(deadline_str: str) -> Dict | None:
    """Check if a deadline is approaching or past."""
    from dateutil import parser as date_parser
    try:
        deadline_date = date_parser.parse(deadline_str)
        now = datetime.now(timezone.utc)
        if deadline_date.tzinfo is None:
            deadline_date = deadline_date.replace(tzinfo=timezone.utc)

        days_remaining = (deadline_date - now).days

        if days_remaining < 0:
            return {
                "severity": 9.0,
                "explanation": f"Deadline EXPIRED {abs(days_remaining)} days ago ({deadline_str}). Immediate action required.",
            }
        elif days_remaining <= DEADLINE_WARN_DAYS:
            severity = max(6.0, 9.0 - (days_remaining / DEADLINE_WARN_DAYS) * 3)
            return {
                "severity": round(severity, 1),
                "explanation": f"Deadline approaching in {days_remaining} days ({deadline_str}). Review required.",
            }
    except (ValueError, TypeError):
        # Not a parseable date — might be a relative condition like "30 days from signing"
        pass
    return None


def _llm_assess_risk(
    edge_type: str, edge_explanation: str,
    obl_text: str, obl_doc_id: str,
    req_text: str, req_doc_id: str,
) -> Dict:
    """LLM pass to confirm risk and assign severity."""
    if client is None:
        return {}

    prompt = RISK_CONFIRMATION_PROMPT.format(
        edge_type=edge_type,
        edge_explanation=edge_explanation,
        obl_doc_id=obl_doc_id,
        obligation_text=obl_text,
        req_doc_id=req_doc_id,
        requirement_text=req_text,
    )

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=[RISK_ASSESSMENT_TOOL],
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "assess_risk":
                return block.input
    except Exception as e:
        print(f"[CCIS] Risk assessment error: {e}")

    return {}


def _create_risk(
    db, doc_id: str, obl, req, rel,
    risk_type: str, severity: float, explanation: str,
    evidence_trail: List[Dict], llm_reasoning: str = None,
) -> Dict:
    """Create and persist a RiskModel."""
    risk_id = str(uuid.uuid4())
    risk = RiskModel(
        risk_id=risk_id,
        obligation_id=obl.obligation_id if obl else None,
        requirement_id=req.requirement_id if req else None,
        relationship_id=rel.relationship_id if rel else None,
        doc_id=doc_id,
        risk_type=risk_type,
        severity_score=severity,
        financial_exposure=obl.financial_exposure if obl else None,
        financial_source="extracted" if (obl and obl.financial_exposure is not None) else "estimated",
        counterparty_importance=5.0,
        counterparty_source="extracted" if (obl and obl.counterparty_tier) else "estimated",
        explanation=explanation,
        evidence_trail=json.dumps(evidence_trail, default=str),
        llm_reasoning=llm_reasoning,
    )
    db.add(risk)

    audit = AuditLogModel(
        log_id=str(uuid.uuid4()),
        doc_id=doc_id,
        stage="detect",
        entity_id=risk_id,
        output_json=json.dumps({
            "risk_type": risk_type,
            "severity_score": severity,
            "explanation": explanation,
        }, default=str),
        model_reasoning=llm_reasoning or explanation,
    )
    db.add(audit)

    return {
        "risk_id": risk_id,
        "risk_type": risk_type,
        "severity_score": severity,
        "explanation": explanation,
    }
