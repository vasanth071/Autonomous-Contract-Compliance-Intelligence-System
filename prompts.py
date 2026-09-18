"""
CCIS Extraction — Prompt templates for Claude tool-use extraction.

Kept separate from logic per spec.
Includes explicit instructions on confidence scoring and field-absence handling.
"""

SYSTEM_PROMPT = """You are a legal-contract and policy-document analyst.
Your job is to extract structured data from document clauses.

CRITICAL RULES:
1. NEVER paraphrase or summarise the source text. Copy the exact clause wording
   into the source_evidence text_span field.
2. If a field is not stated anywhere in the source clause, set it to null and
   mark field_status for that field as "absent_in_source".
3. Only use "extraction_uncertain" when the field IS mentioned but is genuinely
   ambiguous (e.g., "within a reasonable time" for a deadline).
4. Set extraction_confidence as a float 0.0–1.0 reflecting how certain you are
   that the extracted information is correct and complete.
5. Use "present" in field_status for every field you confidently extracted."""

OBLIGATION_EXTRACTION_PROMPT = """Analyse the following document chunk and extract ALL obligations
(things that must be done, delivered, paid, reported, complied with, etc.).

Document: {doc_id} (type: {doc_type})
Page: {page}
Clause: {clause_id}

--- CHUNK TEXT ---
{chunk_text}
--- END CHUNK ---

For each obligation found, call the extract_obligation tool.
If no obligations exist in this chunk, do not call the tool."""

REQUIREMENT_EXTRACTION_PROMPT = """Analyse the following policy/regulatory document chunk and
extract ALL requirements (rules, mandates, standards that must be followed).

Document: {doc_id} (type: {doc_type})
Page: {page}
Clause: {clause_id}

--- CHUNK TEXT ---
{chunk_text}
--- END CHUNK ---

For each requirement found, call the extract_requirement tool.
If no requirements exist in this chunk, do not call the tool."""


# ── Claude tool schemas (function calling) ────────────────────────────────────

OBLIGATION_TOOL = {
    "name": "extract_obligation",
    "description": "Extract a single obligation from the document chunk.",
    "input_schema": {
        "type": "object",
        "properties": {
            "statement": {
                "type": "string",
                "description": "What must be done — the obligation statement."
            },
            "responsible_party": {
                "type": ["string", "null"],
                "description": "Who is responsible. Null if not stated."
            },
            "deadline": {
                "type": ["string", "null"],
                "description": "When it must be done (date or duration). Null if not stated."
            },
            "trigger_condition": {
                "type": ["string", "null"],
                "description": "Condition that triggers the obligation. Null if not stated."
            },
            "obligation_type": {
                "type": "string",
                "enum": ["payment", "reporting", "security", "deliverable", "renewal", "notice", "compliance", "confidentiality", "indemnification", "termination", "other"],
                "description": "Category of the obligation."
            },
            "financial_exposure": {
                "type": ["number", "null"],
                "description": "Monetary amount at stake if stated (e.g. penalty, contract value). Null if not stated."
            },
            "counterparty_tier": {
                "type": ["string", "null"],
                "enum": ["high", "medium", "low", None],
                "description": "Importance tier of the counterparty if determinable. Null if not stated."
            },
            "extraction_confidence": {
                "type": "number",
                "description": "Confidence 0.0–1.0 in the accuracy of this extraction."
            },
            "field_status": {
                "type": "object",
                "description": "Map of field name → 'present' | 'absent_in_source' | 'extraction_uncertain'.",
                "additionalProperties": {
                    "type": "string",
                    "enum": ["present", "absent_in_source", "extraction_uncertain"]
                }
            },
            "text_span": {
                "type": "string",
                "description": "The EXACT text from the source chunk that contains this obligation. Never paraphrase."
            }
        },
        "required": ["statement", "obligation_type", "extraction_confidence", "field_status", "text_span"]
    }
}

REQUIREMENT_TOOL = {
    "name": "extract_requirement",
    "description": "Extract a single policy/regulatory requirement from the document chunk.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rule": {
                "type": "string",
                "description": "The policy or regulatory requirement statement."
            },
            "scope": {
                "type": ["string", "null"],
                "description": "Who or what this requirement applies to. Null if not stated."
            },
            "mandatory": {
                "type": "boolean",
                "description": "True if the requirement is mandatory, false if optional/recommended."
            },
            "extraction_confidence": {
                "type": "number",
                "description": "Confidence 0.0–1.0 in the accuracy of this extraction."
            },
            "field_status": {
                "type": "object",
                "description": "Map of field name → 'present' | 'absent_in_source' | 'extraction_uncertain'.",
                "additionalProperties": {
                    "type": "string",
                    "enum": ["present", "absent_in_source", "extraction_uncertain"]
                }
            },
            "text_span": {
                "type": "string",
                "description": "The EXACT text from the source chunk that contains this requirement. Never paraphrase."
            }
        },
        "required": ["rule", "mandatory", "extraction_confidence", "field_status", "text_span"]
    }
}


# ── Relationship classification prompt ────────────────────────────────────────

RELATIONSHIP_CLASSIFICATION_PROMPT = """You are analysing the relationship between a contractual
obligation and a policy/regulatory requirement.

OBLIGATION (from {obl_doc_id}, clause {obl_clause}):
{obligation_text}

REQUIREMENT (from {req_doc_id}, clause {req_clause}):
{requirement_text}

Classify their relationship by calling the classify_relationship tool.
Consider:
- "supports": the obligation satisfies or aligns with the requirement
- "conflicts": the obligation contradicts or is incompatible with the requirement
- "duplicates": they express the same rule/obligation (possibly with minor wording differences)
- "unaddressed": the obligation is unrelated to this particular requirement
- "policy_conflict": (use only for requirement↔requirement comparisons) two policies contradict

Provide a detailed explanation with evidence from both texts."""

RELATIONSHIP_TOOL = {
    "name": "classify_relationship",
    "description": "Classify the relationship between an obligation and a requirement.",
    "input_schema": {
        "type": "object",
        "properties": {
            "edge_type": {
                "type": "string",
                "enum": ["supports", "conflicts", "duplicates", "unaddressed", "policy_conflict"],
                "description": "The type of relationship."
            },
            "confidence": {
                "type": "number",
                "description": "Confidence 0.0–1.0 in this classification."
            },
            "explanation": {
                "type": "string",
                "description": "Detailed explanation of why this classification was chosen."
            },
            "evidence_a": {
                "type": "string",
                "description": "Key text from the obligation that supports this classification."
            },
            "evidence_b": {
                "type": "string",
                "description": "Key text from the requirement that supports this classification."
            }
        },
        "required": ["edge_type", "confidence", "explanation", "evidence_a", "evidence_b"]
    }
}


# ── Risk confirmation prompt ─────────────────────────────────────────────────

RISK_CONFIRMATION_PROMPT = """You are a compliance risk analyst. Examine the following
relationship between documents and determine the risk severity.

RELATIONSHIP TYPE: {edge_type}
EDGE EXPLANATION: {edge_explanation}

OBLIGATION TEXT (from {obl_doc_id}):
{obligation_text}

REQUIREMENT TEXT (from {req_doc_id}):
{requirement_text}

Assign a severity score from 1 (negligible) to 10 (critical).
Explain exactly what the risk is, what could go wrong, and what action is needed.
Call the assess_risk tool with your findings."""

RISK_ASSESSMENT_TOOL = {
    "name": "assess_risk",
    "description": "Assess the severity and nature of a compliance risk.",
    "input_schema": {
        "type": "object",
        "properties": {
            "severity_score": {
                "type": "number",
                "description": "Severity 1.0–10.0"
            },
            "risk_explanation": {
                "type": "string",
                "description": "Detailed explanation of the risk."
            },
            "recommended_action": {
                "type": "string",
                "description": "What should be done to address this risk."
            }
        },
        "required": ["severity_score", "risk_explanation", "recommended_action"]
    }
}
