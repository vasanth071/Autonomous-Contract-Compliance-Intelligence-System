"""
CCIS Alert Generator — converts Risk Objects into actionable Alert Objects.

Template: "Action required: [obligation] by [deadline] — conflicts with
[policy §X] requiring [Y]. Evidence: [Contract p.X] vs [Policy p.Y]."

Routes alerts to owners based on obligation_type tag.
"""
import json
import uuid
from typing import List, Dict

from backend.database import SessionLocal, RiskModel, ObligationModel, RequirementModel, AlertModel, AuditLogModel


# ── Owner routing by obligation type ──────────────────────────────────────────
OWNER_ROUTING = {
    "payment": "procurement",
    "deliverable": "procurement",
    "reporting": "compliance",
    "compliance": "compliance",
    "security": "compliance",
    "confidentiality": "legal",
    "indemnification": "legal",
    "termination": "legal",
    "notice": "legal",
    "renewal": "legal",
    "other": "compliance",
}


def generate_alerts(doc_id: str) -> List[Dict]:
    """Generate actionable alerts from all risks for a document."""
    db = SessionLocal()
    alerts: List[Dict] = []

    try:
        risks = db.query(RiskModel).filter(
            RiskModel.doc_id == doc_id
        ).order_by(RiskModel.severity_score.desc()).all()

        for risk in risks:
            obl = None
            req = None
            if risk.obligation_id:
                obl = db.query(ObligationModel).filter(
                    ObligationModel.obligation_id == risk.obligation_id
                ).first()
            if risk.requirement_id:
                req = db.query(RequirementModel).filter(
                    RequirementModel.requirement_id == risk.requirement_id
                ).first()

            # Build message
            message = _build_alert_message(risk, obl, req)
            action = _build_action_text(risk, obl, req)
            owner = _determine_owner(obl)
            evidence_refs = json.loads(risk.evidence_trail) if risk.evidence_trail else []

            alert_id = str(uuid.uuid4())
            alert = AlertModel(
                alert_id=alert_id,
                risk_id=risk.risk_id,
                doc_id=doc_id,
                owner_tag=owner,
                priority_band=risk.priority_band,
                message=message,
                action_required=action,
                evidence_refs=json.dumps(evidence_refs, default=str),
            )
            db.add(alert)

            audit = AuditLogModel(
                log_id=str(uuid.uuid4()),
                doc_id=doc_id,
                stage="alert",
                entity_id=alert_id,
                output_json=json.dumps({"message": message, "owner": owner, "priority": risk.priority_band}),
                model_reasoning=f"Alert generated for risk {risk.risk_id} ({risk.risk_type})",
            )
            db.add(audit)

            alerts.append({
                "alert_id": alert_id,
                "risk_id": risk.risk_id,
                "priority_band": risk.priority_band,
                "owner_tag": owner,
                "message": message,
            })

        db.commit()
    finally:
        db.close()

    return alerts


def _build_alert_message(risk: RiskModel, obl, req) -> str:
    """Build a structured, actionable alert message."""
    evidence_trail = json.loads(risk.evidence_trail) if risk.evidence_trail else []

    if risk.risk_type == "policy_conflict" and obl and req:
        obl_ev = json.loads(obl.source_evidence) if obl.source_evidence else {}
        req_ev = json.loads(req.source_evidence) if req.source_evidence else {}

        msg = (
            f"⚠️ POLICY CONFLICT [{risk.priority_band}]: "
            f"{obl.statement[:150]}"
        )
        if obl.deadline:
            msg += f" (deadline: {obl.deadline})"
        msg += f" — conflicts with requirement: {req.rule[:150]}"

        # Add evidence citations
        obl_citation = f"Contract p.{obl_ev.get('page', '?')}" if obl_ev.get('page') else f"Contract clause {obl_ev.get('clause_id', '?')}"
        req_citation = f"Policy p.{req_ev.get('page', '?')}" if req_ev.get('page') else f"Policy clause {req_ev.get('clause_id', '?')}"
        msg += f" (Evidence: {obl_citation} vs {req_citation})"

        return msg

    elif risk.risk_type == "deadline_breach" and obl:
        msg = (
            f"🔴 DEADLINE [{risk.priority_band}]: "
            f"{risk.explanation} "
            f"Obligation: {obl.statement[:150]}"
        )
        return msg

    elif risk.risk_type == "ambiguity" and obl:
        return (
            f"⚡ AMBIGUITY [{risk.priority_band}]: "
            f"{risk.explanation} "
            f"Obligation: {obl.statement[:150]}"
        )

    elif risk.risk_type == "gap" and obl:
        return (
            f"🔍 COVERAGE GAP [{risk.priority_band}]: "
            f"{risk.explanation} "
            f"Obligation: {obl.statement[:150]}"
        )

    return f"⚠️ RISK [{risk.priority_band}]: {risk.explanation or 'Risk detected'}"


def _build_action_text(risk, obl, req) -> str:
    """Generate recommended action text."""
    if risk.risk_type == "policy_conflict":
        return "Review the conflicting clauses and align the contract terms with policy requirements."
    elif risk.risk_type == "deadline_breach":
        return f"Immediate action required to address deadline: {obl.deadline if obl else 'Unknown'}"
    elif risk.risk_type == "ambiguity":
        return "Assign a responsible party and clarify the obligation terms."
    elif risk.risk_type == "gap":
        return "Review whether this obligation requires a corresponding policy or compliance procedure."
    return "Review and address this risk."


def _determine_owner(obl) -> str:
    """Route to owner based on obligation type."""
    if obl and obl.obligation_type:
        return OWNER_ROUTING.get(obl.obligation_type, "compliance")
    return "compliance"
