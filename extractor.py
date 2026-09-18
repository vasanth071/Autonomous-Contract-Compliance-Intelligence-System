"""
CCIS Extraction — Claude LLM extraction engine with local keyword fallback.

Runs a stitching pass on chunks, then calls Claude with tool-use to extract
Obligation and Requirement objects. When the Anthropic API key is not
configured, a fully local keyword/regex engine extracts data instead.

Persists to SQLite and embeds into ChromaDB.
"""
import json
import re
import uuid
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional

from anthropic import Anthropic

from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from backend.database import SessionLocal, ObligationModel, RequirementModel, ChunkModel, AuditLogModel
from backend.knowledge.vector_store import VectorStore
from backend.extraction.prompts import (
    SYSTEM_PROMPT, OBLIGATION_EXTRACTION_PROMPT, REQUIREMENT_EXTRACTION_PROMPT,
    OBLIGATION_TOOL, REQUIREMENT_TOOL
)

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_anthropic_api_key_here" else None


# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL KEYWORD-BASED EXTRACTION (runs when Claude API key is not configured)
# ═══════════════════════════════════════════════════════════════════════════════

# ── Obligation detection patterns ─────────────────────────────────────────────
_OBLIGATION_PATTERNS = [
    re.compile(r'(?:^|(?<=\.\s))([^.]*?\b(?:shall|must|agrees?\s+to|is\s+required\s+to|will\s+(?:provide|deliver|pay|comply|ensure|maintain|submit|report|notify|indemnify|protect))\b[^.]*\.)', re.IGNORECASE | re.MULTILINE),
    re.compile(r'(?:^|(?<=\.\s))([^.]*?\b(?:obligated?\s+to|responsible\s+for|is\s+liable|undertakes?\s+to|covenants?\s+to|warrants?\s+that)\b[^.]*\.)', re.IGNORECASE | re.MULTILINE),
    re.compile(r'(?:^|(?<=\.\s))([^.]*?\b(?:shall\s+not|must\s+not|may\s+not|is\s+prohibited)\b[^.]*\.)', re.IGNORECASE | re.MULTILINE),
]

# ── Obligation type classification keywords ───────────────────────────────────
_OBLIGATION_TYPE_KEYWORDS = {
    "payment":          ["pay", "payment", "fee", "cost", "price", "invoice", "reimburse", "compensat", "amount due", "sum of", "dollar", "usd", "$"],
    "deliverable":      ["deliver", "provide", "supply", "furnish", "submit", "hand over", "produce", "complete"],
    "reporting":        ["report", "notify", "inform", "disclose", "communicate", "update", "submit report", "provide notice"],
    "compliance":       ["comply", "compl", "adhere", "conform", "regulation", "regulatory", "audit", "inspect", "law", "statute"],
    "security":         ["security", "secure", "encrypt", "protect", "safeguard", "confidential", "access control", "firewall", "breach", "cyber"],
    "confidentiality":  ["confidential", "non-disclosure", "nda", "proprietary", "trade secret", "private"],
    "indemnification":  ["indemnif", "hold harmless", "liability", "damages", "loss", "claim"],
    "termination":      ["terminat", "cancel", "end of agreement", "expir", "cease"],
    "notice":           ["notice", "notify", "written notice", "days notice", "prior notice"],
    "renewal":          ["renew", "extend", "continuation", "auto-renew"],
}

# ── Requirement detection patterns ────────────────────────────────────────────
_REQUIREMENT_PATTERNS = [
    re.compile(r'(?:^|(?<=\.\s))([^.]*?\b(?:must\s+comply|shall\s+adhere|required\s+to|in\s+accordance\s+with|is\s+prohibited|mandatory|shall\s+ensure|policy\s+requires|must\s+ensure|must\s+maintain|shall\s+comply)\b[^.]*\.)', re.IGNORECASE | re.MULTILINE),
    re.compile(r'(?:^|(?<=\.\s))([^.]*?\b(?:all\s+(?:parties|employees|contractors|vendors)\s+(?:shall|must|are\s+required))\b[^.]*\.)', re.IGNORECASE | re.MULTILINE),
    re.compile(r'(?:^|(?<=\.\s))([^.]*?\b(?:it\s+is\s+(?:required|mandatory|prohibited)|failure\s+to\s+comply|non-?compliance|violation|penalty\s+for)\b[^.]*\.)', re.IGNORECASE | re.MULTILINE),
    re.compile(r'(?:^|(?<=\.\s))([^.]*?\b(?:standard|guideline|regulation|rule|requirement|specification|criterion|benchmark)\b[^.]*?\b(?:shall|must|require|mandat)\b[^.]*\.)', re.IGNORECASE | re.MULTILINE),
]

# ── Financial amount extraction ───────────────────────────────────────────────
_FINANCIAL_PATTERN = re.compile(
    r'\$\s*([\d,]+(?:\.\d{1,2})?)|'
    r'([\d,]+(?:\.\d{1,2})?)\s*(?:dollars|usd|USD)|'
    r'(?:sum\s+of|amount\s+of|not\s+(?:to\s+)?exceed|up\s+to)\s*\$?\s*([\d,]+(?:\.\d{1,2})?)',
    re.IGNORECASE,
)

# ── Deadline extraction ───────────────────────────────────────────────────────
_DEADLINE_PATTERNS = [
    re.compile(r'(?:within|no\s+later\s+than|by|before|prior\s+to|not\s+to\s+exceed)\s+(\d+)\s+(days?|weeks?|months?|years?|business\s+days?|calendar\s+days?)', re.IGNORECASE),
    re.compile(r'(?:by|before|no\s+later\s+than|prior\s+to)\s+(\w+\s+\d{1,2},?\s+\d{4})', re.IGNORECASE),
    re.compile(r'(?:by|before|no\s+later\s+than|prior\s+to)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', re.IGNORECASE),
    re.compile(r'(\d+)\s+(days?|weeks?|months?)\s+(?:after|from|following)\s+', re.IGNORECASE),
]

# ── Responsible party extraction ──────────────────────────────────────────────
_PARTY_PATTERNS = [
    re.compile(r'(?:the\s+)?((?:Contractor|Provider|Vendor|Supplier|Company|Client|Customer|Employer|Employee|Licensee|Licensor|Lessee|Lessor|Buyer|Seller|Tenant|Landlord|Borrower|Lender|Service\s+Provider|Data\s+Processor|Data\s+Controller|Recipient|Disclosing\s+Party|Receiving\s+Party|First\s+Party|Second\s+Party|Party\s+[AB]))', re.IGNORECASE),
    re.compile(r'"([A-Z][A-Za-z\s&]+?)"(?:\s+(?:shall|must|agrees|is\s+required))', re.MULTILINE),
]


def _classify_obligation_type(text: str) -> str:
    """Classify obligation type using keyword matching."""
    text_lower = text.lower()
    scores = {}
    for obl_type, keywords in _OBLIGATION_TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[obl_type] = score
    if scores:
        return max(scores, key=scores.get)
    return "other"


def _extract_financial(text: str) -> Optional[float]:
    """Extract financial amount from text."""
    m = _FINANCIAL_PATTERN.search(text)
    if m:
        amount_str = m.group(1) or m.group(2) or m.group(3)
        if amount_str:
            try:
                return float(amount_str.replace(",", ""))
            except ValueError:
                pass
    return None


def _extract_deadline(text: str) -> Optional[str]:
    """Extract deadline from text."""
    for pat in _DEADLINE_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(0).strip()
    return None


def _extract_party(text: str) -> Optional[str]:
    """Extract responsible party from text."""
    for pat in _PARTY_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


def _local_extract_obligations(chunk_text: str, chunk: Dict, doc_id: str) -> List[Dict]:
    """Extract obligations using local keyword/regex matching."""
    obligations = []
    seen_statements = set()

    for pattern in _OBLIGATION_PATTERNS:
        for m in pattern.finditer(chunk_text):
            statement = m.group(1).strip()
            if len(statement) < 15:
                continue
            # De-duplicate by normalised text
            norm = " ".join(statement.lower().split())
            if norm in seen_statements:
                continue
            seen_statements.add(norm)

            obl_type = _classify_obligation_type(statement)
            financial = _extract_financial(statement)
            deadline = _extract_deadline(statement)
            party = _extract_party(statement)

            field_status = {
                "statement": "present",
                "responsible_party": "present" if party else "absent_in_source",
                "deadline": "present" if deadline else "absent_in_source",
                "financial_exposure": "present" if financial is not None else "absent_in_source",
                "obligation_type": "present",
            }

            obligations.append({
                "statement": statement,
                "responsible_party": party,
                "deadline": deadline,
                "trigger_condition": None,
                "obligation_type": obl_type,
                "financial_exposure": financial,
                "counterparty_tier": None,
                "extraction_confidence": 0.65,
                "field_status": field_status,
                "text_span": statement,
            })

    # If no pattern matched but the text contains strong obligation keywords,
    # treat the whole chunk as a single obligation
    if not obligations:
        text_lower = chunk_text.lower()
        strong_keywords = ["shall", "must", "agrees to", "is required to", "obligated to"]
        if any(kw in text_lower for kw in strong_keywords) and len(chunk_text.strip()) >= 30:
            # Use first sentence containing keyword
            sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
            for sent in sentences:
                sent_lower = sent.lower()
                if any(kw in sent_lower for kw in strong_keywords) and len(sent.strip()) >= 20:
                    obl_type = _classify_obligation_type(sent)
                    obligations.append({
                        "statement": sent.strip(),
                        "responsible_party": _extract_party(sent),
                        "deadline": _extract_deadline(sent),
                        "trigger_condition": None,
                        "obligation_type": obl_type,
                        "financial_exposure": _extract_financial(sent),
                        "counterparty_tier": None,
                        "extraction_confidence": 0.55,
                        "field_status": {
                            "statement": "present",
                            "responsible_party": "present" if _extract_party(sent) else "absent_in_source",
                            "deadline": "present" if _extract_deadline(sent) else "absent_in_source",
                            "financial_exposure": "present" if _extract_financial(sent) is not None else "absent_in_source",
                            "obligation_type": "present",
                        },
                        "text_span": sent.strip(),
                    })
                    break

    return obligations


def _local_extract_requirements(chunk_text: str, chunk: Dict, doc_id: str) -> List[Dict]:
    """Extract requirements using local keyword/regex matching."""
    requirements = []
    seen_rules = set()

    for pattern in _REQUIREMENT_PATTERNS:
        for m in pattern.finditer(chunk_text):
            rule = m.group(1).strip()
            if len(rule) < 15:
                continue
            norm = " ".join(rule.lower().split())
            if norm in seen_rules:
                continue
            seen_rules.add(norm)

            rule_lower = rule.lower()
            mandatory = any(kw in rule_lower for kw in ["must", "shall", "required", "mandatory", "prohibited"])

            # Try to detect scope
            scope = None
            scope_m = re.search(r'(?:all\s+)?(employees?|contractors?|vendors?|parties|departments?|personnel|staff|users?|organizations?)', rule, re.IGNORECASE)
            if scope_m:
                scope = scope_m.group(0).strip()

            field_status = {
                "rule": "present",
                "scope": "present" if scope else "absent_in_source",
                "mandatory": "present",
            }

            requirements.append({
                "rule": rule,
                "scope": scope,
                "mandatory": mandatory,
                "extraction_confidence": 0.65,
                "field_status": field_status,
                "text_span": rule,
            })

    # Fallback: if no pattern matched but text has requirement keywords
    if not requirements:
        text_lower = chunk_text.lower()
        req_keywords = ["must comply", "shall adhere", "required to", "mandatory", "shall ensure",
                        "must ensure", "in accordance with", "prohibited", "must maintain",
                        "shall comply", "policy", "regulation", "standard", "guideline"]
        if any(kw in text_lower for kw in req_keywords) and len(chunk_text.strip()) >= 30:
            sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
            for sent in sentences:
                sent_lower = sent.lower()
                if any(kw in sent_lower for kw in req_keywords) and len(sent.strip()) >= 20:
                    mandatory = any(kw in sent_lower for kw in ["must", "shall", "required", "mandatory", "prohibited"])
                    requirements.append({
                        "rule": sent.strip(),
                        "scope": None,
                        "mandatory": mandatory,
                        "extraction_confidence": 0.55,
                        "field_status": {
                            "rule": "present",
                            "scope": "absent_in_source",
                            "mandatory": "present",
                        },
                        "text_span": sent.strip(),
                    })
                    break

    return requirements


# ═══════════════════════════════════════════════════════════════════════════════
# CORE EXTRACTION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def _stitch_chunks(chunks: List[Dict]) -> List[Dict]:
    """
    Stitching pass: if a chunk's text ends mid-sentence and the next chunk
    from the same parent_clause_id continues it, concatenate before extraction.
    """
    if not chunks:
        return chunks

    stitched = []
    i = 0
    while i < len(chunks):
        current = dict(chunks[i])
        # Check if current chunk ends mid-sentence (no terminal punctuation)
        while (i + 1 < len(chunks)
               and current["text"]
               and not current["text"].rstrip().endswith(('.', '!', '?', ':', ';'))
               and chunks[i + 1].get("parent_clause_id")
               and chunks[i + 1]["parent_clause_id"] == current.get("parent_clause_id")):
            next_chunk = chunks[i + 1]
            current["text"] = current["text"].rstrip() + " " + next_chunk["text"].lstrip()
            current["char_end"] = next_chunk.get("char_end", current.get("char_end"))
            current["token_count"] = len(current["text"]) // 4
            i += 1
        stitched.append(current)
        i += 1
    return stitched


def extract_obligations_from_chunks(
    chunks: List[Dict], doc_id: str, doc_type: str
) -> List[Dict]:
    """Extract Obligation Objects from stitched chunks using Claude tool-use or local fallback."""
    stitched = _stitch_chunks(chunks)
    all_obligations: List[Dict] = []
    vs = VectorStore()
    db = SessionLocal()

    try:
        for chunk in stitched:
            chunk_text = chunk["text"]
            if not chunk_text.strip() or len(chunk_text.strip()) < 20:
                continue

            # Choose extraction method
            if client is not None:
                prompt = OBLIGATION_EXTRACTION_PROMPT.format(
                    doc_id=doc_id,
                    doc_type=doc_type,
                    page=chunk.get("page", "N/A"),
                    clause_id=chunk.get("clause_id", "N/A"),
                    chunk_text=chunk_text,
                )
                obligations = _call_claude_extraction(
                    prompt, [OBLIGATION_TOOL], "extract_obligation",
                    chunk, doc_id, doc_type
                )
            else:
                obligations = _local_extract_obligations(chunk_text, chunk, doc_id)

            for obl_data in obligations:
                obl_id = str(uuid.uuid4())
                source_evidence = {
                    "doc_id": doc_id,
                    "page": chunk.get("page"),
                    "clause_id": chunk.get("clause_id"),
                    "text_span": obl_data.get("text_span", chunk_text[:500]),
                }

                obl_model = ObligationModel(
                    obligation_id=obl_id,
                    chunk_id=chunk["chunk_id"],
                    doc_id=doc_id,
                    statement=obl_data.get("statement", ""),
                    responsible_party=obl_data.get("responsible_party"),
                    deadline=obl_data.get("deadline"),
                    trigger_condition=obl_data.get("trigger_condition"),
                    obligation_type=obl_data.get("obligation_type", "other"),
                    financial_exposure=obl_data.get("financial_exposure"),
                    counterparty_tier=obl_data.get("counterparty_tier"),
                    extraction_confidence=obl_data.get("extraction_confidence", 0.5),
                    field_status=json.dumps(obl_data.get("field_status", {})),
                    source_evidence=json.dumps(source_evidence),
                )
                db.add(obl_model)

                # Embed into vector store
                vs.upsert_obligation(obl_id, obl_data.get("statement", ""), {
                    "doc_id": doc_id,
                    "obligation_type": obl_data.get("obligation_type", "other"),
                    "clause_id": chunk.get("clause_id", ""),
                })

                # Audit log
                audit = AuditLogModel(
                    log_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    stage="extract",
                    entity_id=obl_id,
                    input_hash=hashlib.sha256(chunk_text.encode()).hexdigest()[:16],
                    output_json=json.dumps(obl_data, default=str),
                    model_reasoning=f"Extracted obligation: {obl_data.get('statement', '')[:100]}",
                )
                db.add(audit)

                all_obligations.append({**obl_data, "obligation_id": obl_id})

        db.commit()
    finally:
        db.close()

    return all_obligations


def extract_requirements_from_chunks(
    chunks: List[Dict], doc_id: str, doc_type: str
) -> List[Dict]:
    """Extract Requirement Objects from stitched chunks using Claude tool-use or local fallback."""
    stitched = _stitch_chunks(chunks)
    all_requirements: List[Dict] = []
    vs = VectorStore()
    db = SessionLocal()

    try:
        for chunk in stitched:
            chunk_text = chunk["text"]
            if not chunk_text.strip() or len(chunk_text.strip()) < 20:
                continue

            # Choose extraction method
            if client is not None:
                prompt = REQUIREMENT_EXTRACTION_PROMPT.format(
                    doc_id=doc_id,
                    doc_type=doc_type,
                    page=chunk.get("page", "N/A"),
                    clause_id=chunk.get("clause_id", "N/A"),
                    chunk_text=chunk_text,
                )
                requirements = _call_claude_extraction(
                    prompt, [REQUIREMENT_TOOL], "extract_requirement",
                    chunk, doc_id, doc_type
                )
            else:
                requirements = _local_extract_requirements(chunk_text, chunk, doc_id)

            for req_data in requirements:
                req_id = str(uuid.uuid4())
                source_evidence = {
                    "doc_id": doc_id,
                    "page": chunk.get("page"),
                    "clause_id": chunk.get("clause_id"),
                    "text_span": req_data.get("text_span", chunk_text[:500]),
                }

                req_model = RequirementModel(
                    requirement_id=req_id,
                    chunk_id=chunk["chunk_id"],
                    doc_id=doc_id,
                    rule=req_data.get("rule", ""),
                    scope=req_data.get("scope"),
                    mandatory=req_data.get("mandatory", True),
                    extraction_confidence=req_data.get("extraction_confidence", 0.5),
                    field_status=json.dumps(req_data.get("field_status", {})),
                    source_evidence=json.dumps(source_evidence),
                )
                db.add(req_model)

                vs.upsert_requirement(req_id, req_data.get("rule", ""), {
                    "doc_id": doc_id,
                    "clause_id": chunk.get("clause_id", ""),
                    "mandatory": str(req_data.get("mandatory", True)),
                })

                audit = AuditLogModel(
                    log_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    stage="extract",
                    entity_id=req_id,
                    input_hash=hashlib.sha256(chunk_text.encode()).hexdigest()[:16],
                    output_json=json.dumps(req_data, default=str),
                    model_reasoning=f"Extracted requirement: {req_data.get('rule', '')[:100]}",
                )
                db.add(audit)

                all_requirements.append({**req_data, "requirement_id": req_id})

        db.commit()
    finally:
        db.close()

    return all_requirements


def _call_claude_extraction(
    prompt: str, tools: List[Dict], tool_name: str,
    chunk: Dict, doc_id: str, doc_type: str
) -> List[Dict]:
    """Call Claude with tool-use and collect all tool calls."""
    if client is None:
        return []

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=[{"role": "user", "content": prompt}],
        )

        results = []
        for block in response.content:
            if block.type == "tool_use" and block.name == tool_name:
                results.append(block.input)
        return results

    except Exception as e:
        print(f"[CCIS] Claude extraction error: {e}")
        return []
