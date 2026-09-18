"""
CCIS Ingestion — Clause-boundary-aware document parser.

Splits PDF/DOCX into structured chunks preserving:
- clause boundaries (Section X, Article X, numbered clauses, lettered sub-clauses)
- page numbers, char offsets
- parent_clause_id for stitched sub-chunks

Never splits across a clause boundary unless the clause exceeds the token ceiling.
"""
import re
import uuid
from typing import List, Dict, Optional

import fitz  # PyMuPDF
from docx import Document as DocxDocument

from backend.config import MAX_CHUNK_TOKENS, OVERLAP_TOKENS


# ── Regex for clause boundaries ──────────────────────────────────────────────
CLAUSE_PATTERNS = [
    re.compile(r"^(?:Section|SECTION)\s+\d+", re.MULTILINE),
    re.compile(r"^(?:Article|ARTICLE)\s+\d+", re.MULTILINE),
    re.compile(r"^\d+\.\d*\s+", re.MULTILINE),                # 1.  1.1  1.2.3
    re.compile(r"^\([a-z]\)\s+", re.MULTILINE),                # (a) (b) (c)
    re.compile(r"^[A-Z]\.\s+", re.MULTILINE),                  # A. B. C.
    re.compile(r"^(?:Clause|CLAUSE)\s+\d+", re.MULTILINE),
]


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def _detect_clause_id(text: str) -> Optional[str]:
    """Extract a clause identifier from the start of a text block."""
    patterns = [
        re.compile(r"^((?:Section|SECTION)\s+\d+(?:\.\d+)*)"),
        re.compile(r"^((?:Article|ARTICLE)\s+\d+(?:\.\d+)*)"),
        re.compile(r"^((?:Clause|CLAUSE)\s+\d+(?:\.\d+)*)"),
        re.compile(r"^(\d+(?:\.\d+)+)"),
        re.compile(r"^(\d+\.)\s"),
    ]
    for pat in patterns:
        m = pat.match(text.strip())
        if m:
            return m.group(1).strip().rstrip(".")
    return None


def _split_by_clauses(full_text: str) -> List[Dict]:
    """Split text on clause boundaries, returning sections with char offsets."""
    # Find all clause-boundary positions
    boundary_positions = set()
    boundary_positions.add(0)
    for pat in CLAUSE_PATTERNS:
        for m in pat.finditer(full_text):
            boundary_positions.add(m.start())
    boundary_positions = sorted(boundary_positions)

    sections = []
    for i, start in enumerate(boundary_positions):
        end = boundary_positions[i + 1] if i + 1 < len(boundary_positions) else len(full_text)
        text = full_text[start:end].strip()
        if text:
            clause_id = _detect_clause_id(text)
            sections.append({
                "text": text,
                "char_start": start,
                "char_end": end,
                "clause_id": clause_id,
            })
    return sections


def _token_split_section(section: Dict, doc_id: str, page: Optional[int],
                         max_tokens: int, overlap_tokens: int) -> List[Dict]:
    """If a single clause section exceeds max_tokens, split with overlap and tag parent_clause_id."""
    text = section["text"]
    tokens_est = _estimate_tokens(text)
    if tokens_est <= max_tokens:
        return [{
            "chunk_id": str(uuid.uuid4()),
            "doc_id": doc_id,
            "page": page,
            "clause_id": section.get("clause_id"),
            "parent_clause_id": None,
            "text": text,
            "char_start": section["char_start"],
            "char_end": section["char_end"],
            "token_count": tokens_est,
        }]

    # Sub-split with overlap
    parent_clause_id = section.get("clause_id") or str(uuid.uuid4())[:8]
    chunks = []
    char_step = max_tokens * 4  # approx chars per max_tokens
    overlap_chars = overlap_tokens * 4
    pos = 0
    sub_idx = 0
    while pos < len(text):
        end = min(pos + char_step, len(text))
        chunk_text = text[pos:end].strip()
        if chunk_text:
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "page": page,
                "clause_id": f"{parent_clause_id}.sub{sub_idx}",
                "parent_clause_id": parent_clause_id,
                "text": chunk_text,
                "char_start": section["char_start"] + pos,
                "char_end": section["char_start"] + end,
                "token_count": _estimate_tokens(chunk_text),
            })
            sub_idx += 1
        pos = end - overlap_chars if end < len(text) else end
    return chunks


# ── PDF Parser ────────────────────────────────────────────────────────────────

def parse_pdf(filepath: str, doc_id: str) -> List[Dict]:
    """Parse a PDF into clause-boundary-aware chunks."""
    doc = fitz.open(filepath)
    all_chunks: List[Dict] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        if not page_text.strip():
            continue

        sections = _split_by_clauses(page_text)
        for section in sections:
            chunks = _token_split_section(
                section, doc_id, page_num + 1, MAX_CHUNK_TOKENS, OVERLAP_TOKENS
            )
            all_chunks.extend(chunks)

    doc.close()
    return all_chunks


# ── DOCX Parser ──────────────────────────────────────────────────────────────

def parse_docx(filepath: str, doc_id: str) -> List[Dict]:
    """Parse a DOCX into clause-boundary-aware chunks."""
    docx_doc = DocxDocument(filepath)
    full_text = "\n".join(p.text for p in docx_doc.paragraphs if p.text.strip())

    sections = _split_by_clauses(full_text)
    all_chunks: List[Dict] = []
    for section in sections:
        chunks = _token_split_section(
            section, doc_id, None, MAX_CHUNK_TOKENS, OVERLAP_TOKENS
        )
        all_chunks.extend(chunks)
    return all_chunks


# ── Unified parser ────────────────────────────────────────────────────────────

def parse_document(filepath: str, doc_id: str) -> List[Dict]:
    """Route to the correct parser based on file extension."""
    ext = filepath.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return parse_pdf(filepath, doc_id)
    elif ext in ("docx", "doc"):
        return parse_docx(filepath, doc_id)
    else:
        raise ValueError(f"Unsupported file type: .{ext}")
