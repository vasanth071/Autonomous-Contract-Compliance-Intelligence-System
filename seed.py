"""
CCIS Sample Data Seed — generates synthetic documents and populates the database.

Creates a vendor contract and data privacy policy with a deliberate conflict:
- Contract: 30-day termination notice
- Policy: 60-day termination notice required

This guarantees a Critical risk shows up in the demo.
"""
import os
import sys
import json
import uuid
import hashlib
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db, SessionLocal, DocumentModel, ChunkModel, ObligationModel, RequirementModel, RelationshipModel, RiskModel, AlertModel, AuditLogModel
from backend.knowledge.vector_store import VectorStore


def seed():
    """Populate the database with synthetic sample data."""
    print("[SEED] Initialising database...")
    init_db()

    db = SessionLocal()
    vs = VectorStore()

    try:
        # Check if already seeded
        if db.query(DocumentModel).count() > 0:
            print("[SEED] Database already contains data. Clearing and re-seeding...")
            for tbl in [AuditLogModel, AlertModel, RiskModel, RelationshipModel,
                        RequirementModel, ObligationModel, ChunkModel, DocumentModel]:
                db.query(tbl).delete()
            db.commit()

        # ── Document 1: Vendor Service Agreement ─────────────────────────
        contract_id = str(uuid.uuid4())
        contract = DocumentModel(
            doc_id=contract_id,
            filename="Vendor_Service_Agreement_AcmeCorp.pdf",
            doc_type="contract",
            parties=json.dumps(["AcmeCorp", "DataFlow Inc."]),
            effective_date="2024-01-15",
            version="2.1",
            status="done",
        )
        db.add(contract)

        # ── Document 2: Data Privacy & Security Policy ────────────────────
        policy_id = str(uuid.uuid4())
        policy = DocumentModel(
            doc_id=policy_id,
            filename="Corporate_Data_Privacy_Security_Policy.pdf",
            doc_type="policy",
            parties=json.dumps(["Internal"]),
            effective_date="2023-06-01",
            version="3.0",
            status="done",
        )
        db.add(policy)
        db.commit()

        # ── Contract Chunks & Obligations ─────────────────────────────────
        contract_clauses = [
            {
                "clause_id": "Section 3.1",
                "page": 3,
                "text": "Section 3.1 — Termination Notice. Either party may terminate this Agreement by providing thirty (30) calendar days' written notice to the other party. Notice shall be delivered via certified mail or email to the designated contract administrator.",
                "obligation": {
                    "statement": "Either party may terminate this Agreement by providing thirty (30) calendar days' written notice to the other party.",
                    "responsible_party": "Either party (AcmeCorp or DataFlow Inc.)",
                    "deadline": "30 calendar days written notice",
                    "trigger_condition": "Decision to terminate the agreement",
                    "obligation_type": "notice",
                    "financial_exposure": None,
                    "counterparty_tier": "high",
                    "extraction_confidence": 0.95,
                    "field_status": {
                        "statement": "present",
                        "responsible_party": "present",
                        "deadline": "present",
                        "trigger_condition": "present",
                        "obligation_type": "present",
                        "financial_exposure": "absent_in_source",
                        "counterparty_tier": "extraction_uncertain",
                    },
                },
            },
            {
                "clause_id": "Section 5.2",
                "page": 5,
                "text": "Section 5.2 — Data Processing. DataFlow Inc. shall process all personal data received from AcmeCorp in accordance with applicable data protection laws, including GDPR where applicable. DataFlow Inc. shall implement appropriate technical and organisational measures to ensure a level of security appropriate to the risk.",
                "obligation": {
                    "statement": "DataFlow Inc. shall process all personal data received from AcmeCorp in accordance with applicable data protection laws and implement appropriate technical and organisational security measures.",
                    "responsible_party": "DataFlow Inc.",
                    "deadline": None,
                    "trigger_condition": "Receipt of personal data from AcmeCorp",
                    "obligation_type": "compliance",
                    "financial_exposure": None,
                    "counterparty_tier": "high",
                    "extraction_confidence": 0.92,
                    "field_status": {
                        "statement": "present",
                        "responsible_party": "present",
                        "deadline": "absent_in_source",
                        "trigger_condition": "present",
                        "obligation_type": "present",
                        "financial_exposure": "absent_in_source",
                        "counterparty_tier": "extraction_uncertain",
                    },
                },
            },
            {
                "clause_id": "Section 7.1",
                "page": 7,
                "text": "Section 7.1 — Annual Security Audit. DataFlow Inc. shall undergo an independent security audit annually, no later than December 31st of each calendar year, and provide AcmeCorp with a copy of the audit report within fifteen (15) business days of its completion.",
                "obligation": {
                    "statement": "DataFlow Inc. shall undergo an independent security audit annually (by Dec 31) and provide AcmeCorp with the audit report within 15 business days.",
                    "responsible_party": "DataFlow Inc.",
                    "deadline": "December 31st annually; report within 15 business days",
                    "trigger_condition": "Annual calendar cycle",
                    "obligation_type": "reporting",
                    "financial_exposure": None,
                    "counterparty_tier": "high",
                    "extraction_confidence": 0.97,
                    "field_status": {
                        "statement": "present",
                        "responsible_party": "present",
                        "deadline": "present",
                        "trigger_condition": "present",
                        "obligation_type": "present",
                        "financial_exposure": "absent_in_source",
                        "counterparty_tier": "extraction_uncertain",
                    },
                },
            },
            {
                "clause_id": "Section 8.3",
                "page": 8,
                "text": "Section 8.3 — Service Level Penalties. In the event that DataFlow Inc. fails to meet the 99.5% uptime SLA for three (3) consecutive months, AcmeCorp shall be entitled to a service credit of fifteen percent (15%) of the monthly service fee for each month of non-compliance, up to a maximum of $50,000 per quarter.",
                "obligation": {
                    "statement": "DataFlow Inc. must maintain 99.5% uptime SLA. Failure for 3 consecutive months triggers a 15% service credit per month, capped at $50,000/quarter.",
                    "responsible_party": "DataFlow Inc.",
                    "deadline": None,
                    "trigger_condition": "Failure to meet 99.5% uptime for 3 consecutive months",
                    "obligation_type": "payment",
                    "financial_exposure": 50000.0,
                    "counterparty_tier": "high",
                    "extraction_confidence": 0.94,
                    "field_status": {
                        "statement": "present",
                        "responsible_party": "present",
                        "deadline": "absent_in_source",
                        "trigger_condition": "present",
                        "obligation_type": "present",
                        "financial_exposure": "present",
                        "counterparty_tier": "extraction_uncertain",
                    },
                },
            },
            {
                "clause_id": "Section 10.1",
                "page": 10,
                "text": "Section 10.1 — Data Breach Notification. In the event of a confirmed data breach affecting AcmeCorp's data, DataFlow Inc. shall notify AcmeCorp within forty-eight (48) hours of becoming aware of the breach. Notification shall include the nature of the breach, categories of data affected, estimated number of records, and remedial measures taken or proposed.",
                "obligation": {
                    "statement": "DataFlow Inc. shall notify AcmeCorp within 48 hours of a confirmed data breach, including breach details, affected data categories, record count, and remedial measures.",
                    "responsible_party": "DataFlow Inc.",
                    "deadline": "48 hours from breach awareness",
                    "trigger_condition": "Confirmed data breach affecting AcmeCorp's data",
                    "obligation_type": "security",
                    "financial_exposure": None,
                    "counterparty_tier": "high",
                    "extraction_confidence": 0.96,
                    "field_status": {
                        "statement": "present",
                        "responsible_party": "present",
                        "deadline": "present",
                        "trigger_condition": "present",
                        "obligation_type": "present",
                        "financial_exposure": "absent_in_source",
                        "counterparty_tier": "extraction_uncertain",
                    },
                },
            },
            {
                "clause_id": "Section 12.2",
                "page": 12,
                "text": "Section 12.2 — Renewal. This Agreement shall automatically renew for successive one-year periods unless either party provides written notice of non-renewal at least thirty (30) days prior to the expiration of the then-current term.",
                "obligation": {
                    "statement": "Agreement auto-renews annually unless either party provides 30 days' written notice of non-renewal before term expiration.",
                    "responsible_party": "Either party",
                    "deadline": (datetime.now(timezone.utc) + timedelta(days=25)).strftime("%Y-%m-%d"),
                    "trigger_condition": "Approaching end of current term",
                    "obligation_type": "renewal",
                    "financial_exposure": None,
                    "counterparty_tier": "high",
                    "extraction_confidence": 0.93,
                    "field_status": {
                        "statement": "present",
                        "responsible_party": "present",
                        "deadline": "present",
                        "trigger_condition": "present",
                        "obligation_type": "present",
                        "financial_exposure": "absent_in_source",
                        "counterparty_tier": "extraction_uncertain",
                    },
                },
            },
        ]

        # ── Policy Chunks & Requirements ──────────────────────────────────
        policy_clauses = [
            {
                "clause_id": "Policy 4.2",
                "page": 4,
                "text": "Policy 4.2 — Vendor Termination Requirements. All vendor agreements must include a minimum sixty (60) calendar day termination notice period. Shorter notice periods are not permitted without approval from the Chief Legal Officer and must be documented with a risk exception.",
                "requirement": {
                    "rule": "All vendor agreements must include a minimum 60 calendar day termination notice period. Shorter periods require CLO approval and a documented risk exception.",
                    "scope": "All vendor agreements",
                    "mandatory": True,
                    "extraction_confidence": 0.98,
                    "field_status": {
                        "rule": "present",
                        "scope": "present",
                        "mandatory": "present",
                    },
                },
            },
            {
                "clause_id": "Policy 6.1",
                "page": 6,
                "text": "Policy 6.1 — Data Processing Standards. All third-party data processors must comply with the organisation's data protection framework, which requires: (a) encryption of data at rest and in transit using AES-256 or equivalent, (b) annual SOC 2 Type II certification, (c) data localisation within approved jurisdictions.",
                "requirement": {
                    "rule": "Third-party data processors must comply with: AES-256 encryption at rest and in transit, annual SOC 2 Type II certification, and data localisation within approved jurisdictions.",
                    "scope": "All third-party data processors",
                    "mandatory": True,
                    "extraction_confidence": 0.96,
                    "field_status": {
                        "rule": "present",
                        "scope": "present",
                        "mandatory": "present",
                    },
                },
            },
            {
                "clause_id": "Policy 8.1",
                "page": 8,
                "text": "Policy 8.1 — Breach Notification Timeline. All data processing agreements must require the processor to notify the organisation within twenty-four (24) hours of a confirmed data breach, not exceeding the timeline mandated by applicable regulations (e.g., GDPR Article 33).",
                "requirement": {
                    "rule": "Data processing agreements must require breach notification within 24 hours of confirmation, in compliance with GDPR Article 33.",
                    "scope": "All data processing agreements",
                    "mandatory": True,
                    "extraction_confidence": 0.97,
                    "field_status": {
                        "rule": "present",
                        "scope": "present",
                        "mandatory": "present",
                    },
                },
            },
            {
                "clause_id": "Policy 9.3",
                "page": 9,
                "text": "Policy 9.3 — Security Audit Requirements. Vendors processing sensitive data must provide evidence of an independent security audit (SOC 2 Type II or ISO 27001) conducted within the past twelve (12) months. Audit reports must be reviewed by the Information Security team before contract renewal.",
                "requirement": {
                    "rule": "Vendors processing sensitive data must provide SOC 2 Type II or ISO 27001 audit evidence within the past 12 months, reviewed by InfoSec before renewal.",
                    "scope": "Vendors processing sensitive data",
                    "mandatory": True,
                    "extraction_confidence": 0.95,
                    "field_status": {
                        "rule": "present",
                        "scope": "present",
                        "mandatory": "present",
                    },
                },
            },
            {
                "clause_id": "Policy 11.2",
                "page": 11,
                "text": "Policy 11.2 — Financial Exposure Limits. No single vendor agreement shall expose the organisation to penalties or service credits exceeding $25,000 per quarter without executive committee approval.",
                "requirement": {
                    "rule": "No single vendor agreement shall expose the organisation to penalties exceeding $25,000 per quarter without executive committee approval.",
                    "scope": "All vendor agreements",
                    "mandatory": True,
                    "extraction_confidence": 0.94,
                    "field_status": {
                        "rule": "present",
                        "scope": "present",
                        "mandatory": "present",
                    },
                },
            },
        ]

        # ── Insert chunks and obligations ─────────────────────────────────
        print("[SEED] Creating contract obligations...")
        obligation_ids = []
        for clause in contract_clauses:
            chunk_id = str(uuid.uuid4())
            db.add(ChunkModel(
                chunk_id=chunk_id,
                doc_id=contract_id,
                page=clause["page"],
                clause_id=clause["clause_id"],
                text=clause["text"],
                char_start=0,
                char_end=len(clause["text"]),
                token_count=len(clause["text"]) // 4,
            ))

            obl_id = str(uuid.uuid4())
            obl_data = clause["obligation"]
            source_evidence = {
                "doc_id": contract_id,
                "page": clause["page"],
                "clause_id": clause["clause_id"],
                "text_span": clause["text"],
            }

            db.add(ObligationModel(
                obligation_id=obl_id,
                chunk_id=chunk_id,
                doc_id=contract_id,
                statement=obl_data["statement"],
                responsible_party=obl_data.get("responsible_party"),
                deadline=obl_data.get("deadline"),
                trigger_condition=obl_data.get("trigger_condition"),
                obligation_type=obl_data["obligation_type"],
                financial_exposure=obl_data.get("financial_exposure"),
                counterparty_tier=obl_data.get("counterparty_tier"),
                extraction_confidence=obl_data["extraction_confidence"],
                field_status=json.dumps(obl_data["field_status"]),
                source_evidence=json.dumps(source_evidence),
            ))
            obligation_ids.append(obl_id)

            vs.upsert_obligation(obl_id, obl_data["statement"], {
                "doc_id": contract_id,
                "obligation_type": obl_data["obligation_type"],
                "clause_id": clause["clause_id"],
            })

        # ── Insert chunks and requirements ────────────────────────────────
        print("[SEED] Creating policy requirements...")
        requirement_ids = []
        for clause in policy_clauses:
            chunk_id = str(uuid.uuid4())
            db.add(ChunkModel(
                chunk_id=chunk_id,
                doc_id=policy_id,
                page=clause["page"],
                clause_id=clause["clause_id"],
                text=clause["text"],
                char_start=0,
                char_end=len(clause["text"]),
                token_count=len(clause["text"]) // 4,
            ))

            req_id = str(uuid.uuid4())
            req_data = clause["requirement"]
            source_evidence = {
                "doc_id": policy_id,
                "page": clause["page"],
                "clause_id": clause["clause_id"],
                "text_span": clause["text"],
            }

            db.add(RequirementModel(
                requirement_id=req_id,
                chunk_id=chunk_id,
                doc_id=policy_id,
                rule=req_data["rule"],
                scope=req_data.get("scope"),
                mandatory=req_data["mandatory"],
                extraction_confidence=req_data["extraction_confidence"],
                field_status=json.dumps(req_data["field_status"]),
                source_evidence=json.dumps(source_evidence),
            ))
            requirement_ids.append(req_id)

            vs.upsert_requirement(req_id, req_data["rule"], {
                "doc_id": policy_id,
                "clause_id": clause["clause_id"],
                "mandatory": str(req_data["mandatory"]),
            })

        db.commit()

        # ── Create Relationships ──────────────────────────────────────────
        print("[SEED] Creating cross-document relationships...")
        relationships_data = [
            # CONFLICT: 30-day notice vs 60-day policy
            {
                "obl_idx": 0, "req_idx": 0, "edge_type": "conflicts",
                "confidence": 0.97,
                "explanation": "The contract specifies a 30-day termination notice period (Section 3.1), which directly violates the corporate policy requiring a minimum 60-day termination notice period (Policy 4.2). This is a clear policy violation that requires immediate resolution.",
                "evidence_a": "Either party may terminate this Agreement by providing thirty (30) calendar days' written notice",
                "evidence_b": "All vendor agreements must include a minimum sixty (60) calendar day termination notice period",
            },
            # SUPPORTS: Data processing compliance
            {
                "obl_idx": 1, "req_idx": 1, "edge_type": "supports",
                "confidence": 0.82,
                "explanation": "The contract's data processing obligation (Section 5.2) broadly aligns with Policy 6.1's data processing standards. However, the contract does not explicitly specify AES-256 encryption, SOC 2 Type II, or data localisation requirements — it uses the more general phrase 'appropriate technical and organisational measures'.",
                "evidence_a": "DataFlow Inc. shall implement appropriate technical and organisational measures to ensure a level of security appropriate to the risk",
                "evidence_b": "AES-256 encryption at rest and in transit, annual SOC 2 Type II certification, and data localisation within approved jurisdictions",
            },
            # CONFLICT: 48-hour breach notification vs 24-hour policy
            {
                "obl_idx": 4, "req_idx": 2, "edge_type": "conflicts",
                "confidence": 0.95,
                "explanation": "The contract requires breach notification within 48 hours (Section 10.1), but Policy 8.1 mandates notification within 24 hours. The contract's timeline is twice as long as the policy requirement, creating a compliance gap.",
                "evidence_a": "DataFlow Inc. shall notify AcmeCorp within forty-eight (48) hours of becoming aware of the breach",
                "evidence_b": "require the processor to notify the organisation within twenty-four (24) hours of a confirmed data breach",
            },
            # SUPPORTS: Security audit
            {
                "obl_idx": 2, "req_idx": 3, "edge_type": "supports",
                "confidence": 0.88,
                "explanation": "The contract's annual security audit requirement (Section 7.1) aligns with Policy 9.3's audit requirements. Both require annual independent security audits, though the contract does not specify SOC 2 Type II or ISO 27001 specifically.",
                "evidence_a": "DataFlow Inc. shall undergo an independent security audit annually",
                "evidence_b": "Vendors processing sensitive data must provide evidence of an independent security audit (SOC 2 Type II or ISO 27001)",
            },
            # CONFLICT: $50K penalty cap vs $25K policy limit
            {
                "obl_idx": 3, "req_idx": 4, "edge_type": "conflicts",
                "confidence": 0.93,
                "explanation": "The contract allows penalties up to $50,000 per quarter (Section 8.3), which exceeds Policy 11.2's limit of $25,000 per quarter without executive committee approval. This financial exposure exceeds the policy threshold.",
                "evidence_a": "up to a maximum of $50,000 per quarter",
                "evidence_b": "No single vendor agreement shall expose the organisation to penalties or service credits exceeding $25,000 per quarter",
            },
        ]

        rel_ids = []
        for rel_data in relationships_data:
            rel_id = str(uuid.uuid4())
            db.add(RelationshipModel(
                relationship_id=rel_id,
                obligation_id=obligation_ids[rel_data["obl_idx"]],
                requirement_id=requirement_ids[rel_data["req_idx"]],
                edge_type=rel_data["edge_type"],
                confidence=rel_data["confidence"],
                explanation=rel_data["explanation"],
                evidence_a=rel_data["evidence_a"],
                evidence_b=rel_data["evidence_b"],
            ))
            rel_ids.append(rel_id)

        db.commit()

        # ── Create Risks ──────────────────────────────────────────────────
        print("[SEED] Creating risks...")
        risk_data_list = [
            # Critical: 30 vs 60 day notice
            {
                "obl_idx": 0, "req_idx": 0, "rel_idx": 0,
                "risk_type": "policy_conflict",
                "severity_score": 8.5,
                "priority_band": "Critical",
                "explanation": "CRITICAL: Contract termination notice period (30 days) violates corporate policy minimum (60 days). This non-compliance requires immediate remediation — either amend the contract or obtain CLO risk exception.",
                "llm_reasoning": "The 30-day notice period is exactly half the required 60-day minimum. This creates a significant compliance risk: if the vendor terminates with only 30 days notice, the organisation may not have sufficient time to transition services, potentially causing operational disruption.",
            },
            # High: 48-hour vs 24-hour breach notification
            {
                "obl_idx": 4, "req_idx": 2, "rel_idx": 2,
                "risk_type": "policy_conflict",
                "severity_score": 7.2,
                "priority_band": "High",
                "explanation": "Contract breach notification timeline (48 hours) exceeds policy requirement (24 hours). The additional 24-hour delay could expose the organisation to regulatory penalties under GDPR Article 33.",
                "llm_reasoning": "GDPR Article 33 requires notification within 72 hours. The policy adds a safety margin with 24 hours. The contract's 48-hour window still falls within GDPR timelines but violates internal policy. Risk: delayed incident response and potential regulatory scrutiny.",
            },
            # High: $50K vs $25K financial exposure
            {
                "obl_idx": 3, "req_idx": 4, "rel_idx": 4,
                "risk_type": "policy_conflict",
                "severity_score": 6.8,
                "priority_band": "High",
                "financial_exposure": 50000.0,
                "financial_source": "extracted",
                "explanation": "Contract penalty cap ($50,000/quarter) exceeds policy financial exposure limit ($25,000/quarter) by 100%. Executive committee approval required per Policy 11.2.",
                "llm_reasoning": "The $50,000 quarterly exposure is double the policy threshold. This likely requires executive committee approval that may not have been obtained. Recommended action: verify if approval exists or renegotiate the penalty cap.",
            },
            # Medium: Deadline approaching for renewal
            {
                "obl_idx": 5, "req_idx": None, "rel_idx": None,
                "risk_type": "deadline_breach",
                "severity_score": 6.0,
                "priority_band": "High",
                "explanation": f"Renewal non-renewal notice deadline approaching in ~25 days. If automatic renewal is not desired, written notice must be sent promptly.",
                "llm_reasoning": "Automatic renewal clause with approaching deadline. If the organisation intends to renegotiate terms (especially the identified policy conflicts), notice of non-renewal must be sent before the deadline.",
            },
        ]

        risk_ids = []
        for rd in risk_data_list:
            risk_id = str(uuid.uuid4())
            obl = db.query(ObligationModel).filter(
                ObligationModel.obligation_id == obligation_ids[rd["obl_idx"]]
            ).first()

            evidence_trail = []
            obl_ev = json.loads(obl.source_evidence) if obl and obl.source_evidence else {}
            evidence_trail.append({
                "label": "Contract obligation",
                "doc_id": contract_id,
                "page": obl_ev.get("page"),
                "clause_id": obl_ev.get("clause_id"),
                "text": obl_ev.get("text_span", obl.statement[:300]) if obl else "",
            })

            if rd["req_idx"] is not None:
                req = db.query(RequirementModel).filter(
                    RequirementModel.requirement_id == requirement_ids[rd["req_idx"]]
                ).first()
                if req:
                    req_ev = json.loads(req.source_evidence) if req.source_evidence else {}
                    evidence_trail.append({
                        "label": "Policy requirement",
                        "doc_id": policy_id,
                        "page": req_ev.get("page"),
                        "clause_id": req_ev.get("clause_id"),
                        "text": req_ev.get("text_span", req.rule[:300]),
                    })

            risk = RiskModel(
                risk_id=risk_id,
                obligation_id=obligation_ids[rd["obl_idx"]],
                requirement_id=requirement_ids[rd["req_idx"]] if rd["req_idx"] is not None else None,
                relationship_id=rel_ids[rd["rel_idx"]] if rd["rel_idx"] is not None else None,
                doc_id=contract_id,
                risk_type=rd["risk_type"],
                severity_score=rd["severity_score"],
                priority_band=rd["priority_band"],
                financial_exposure=rd.get("financial_exposure"),
                financial_source=rd.get("financial_source", "estimated"),
                explanation=rd["explanation"],
                evidence_trail=json.dumps(evidence_trail, default=str),
                llm_reasoning=rd["llm_reasoning"],
            )
            db.add(risk)
            risk_ids.append(risk_id)

        db.commit()

        # ── Create Alerts ─────────────────────────────────────────────────
        print("[SEED] Creating alerts...")
        alert_messages = [
            {
                "risk_idx": 0,
                "owner": "legal",
                "message": "⚠️ POLICY CONFLICT [Critical]: Contract termination notice (30 days, Section 3.1) violates corporate policy minimum (60 days, Policy 4.2). This non-compliance requires immediate remediation. (Evidence: Contract p.3 vs Policy p.4)",
                "action": "Amend the contract to extend the termination notice period to 60 days, or obtain Chief Legal Officer approval for a risk exception per Policy 4.2.",
            },
            {
                "risk_idx": 1,
                "owner": "compliance",
                "message": "⚠️ POLICY CONFLICT [High]: Contract breach notification timeline (48 hours, Section 10.1) exceeds policy requirement (24 hours, Policy 8.1). The 24-hour delay gap may impact GDPR compliance. (Evidence: Contract p.10 vs Policy p.8)",
                "action": "Negotiate amendment to reduce breach notification timeline from 48 to 24 hours to align with Policy 8.1 and maintain GDPR compliance margin.",
            },
            {
                "risk_idx": 2,
                "owner": "procurement",
                "message": "⚠️ POLICY CONFLICT [High]: Contract penalty exposure ($50,000/quarter, Section 8.3) exceeds policy limit ($25,000/quarter, Policy 11.2). Executive committee approval required. (Evidence: Contract p.8 vs Policy p.11)",
                "action": "Obtain executive committee approval for the elevated financial exposure, or renegotiate the penalty cap to $25,000/quarter.",
            },
            {
                "risk_idx": 3,
                "owner": "legal",
                "message": "🔴 DEADLINE [High]: Renewal non-renewal notice deadline approaching in ~25 days (Section 12.2). If automatic renewal is not desired, send written notice immediately.",
                "action": "Decide whether to renew (especially given identified policy conflicts) and send non-renewal notice if needed before the deadline.",
            },
        ]

        for ad in alert_messages:
            risk = db.query(RiskModel).filter(RiskModel.risk_id == risk_ids[ad["risk_idx"]]).first()
            alert_id = str(uuid.uuid4())
            db.add(AlertModel(
                alert_id=alert_id,
                risk_id=risk.risk_id,
                doc_id=contract_id,
                owner_tag=ad["owner"],
                priority_band=risk.priority_band,
                message=ad["message"],
                action_required=ad["action"],
                evidence_refs=risk.evidence_trail,
            ))

        db.commit()

        # ── Audit Log entries ─────────────────────────────────────────────
        print("[SEED] Creating audit trail...")
        stages = [
            ("parse", contract_id, "Document parsed: 6 clauses extracted from Vendor Service Agreement"),
            ("parse", policy_id, "Document parsed: 5 clauses extracted from Data Privacy & Security Policy"),
            ("extract", contract_id, "Extracted 6 obligations from contract (avg confidence: 0.945)"),
            ("extract", policy_id, "Extracted 5 requirements from policy (avg confidence: 0.96)"),
            ("map", contract_id, "Cross-document mapping complete: 5 relationships identified (3 conflicts, 2 supports)"),
            ("detect", contract_id, "Risk detection complete: 4 risks identified (1 Critical, 2 High, 1 Medium)"),
            ("prioritize", contract_id, "Risk prioritisation complete using weighted scoring"),
            ("alert", contract_id, "Generated 4 actionable alerts routed to legal (2), compliance (1), procurement (1)"),
            ("complete", contract_id, "Full pipeline completed successfully"),
        ]

        for stage, did, reasoning in stages:
            db.add(AuditLogModel(
                log_id=str(uuid.uuid4()),
                doc_id=did,
                document_version="2.1" if did == contract_id else "3.0",
                stage=stage,
                model_reasoning=reasoning,
            ))

        db.commit()

        # ── Export graph ──────────────────────────────────────────────────
        print("[SEED] Exporting graph...")
        from backend.mapping.graph_builder import _export_graph
        _export_graph(db)

        print("[SEED] ✅ Seeding complete!")
        print(f"  📄 Documents: 2 (contract + policy)")
        print(f"  📋 Obligations: 6")
        print(f"  📏 Requirements: 5")
        print(f"  🔗 Relationships: 5 (3 conflicts, 2 supports)")
        print(f"  ⚠️  Risks: 4 (1 Critical, 2 High, 1 Medium)")
        print(f"  🔔 Alerts: 4")
        print(f"  📝 Audit entries: {len(stages)}")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
