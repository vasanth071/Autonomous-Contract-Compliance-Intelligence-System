# CCIS — Contract–Compliance Intelligence System

AI-powered pipeline that ingests contracts and policy documents, extracts obligations, maps cross-document compliance relationships, detects risks, and delivers actionable, evidence-traceable alerts.

## Quick Start

### 1. Setup
```bash
# Install Python dependencies
python -m pip install fastapi uvicorn sqlalchemy pydantic anthropic chromadb pymupdf python-docx rank-bm25 networkx python-dotenv aiofiles python-multipart python-dateutil

# Install frontend dependencies
cd frontend && npm install && cd ..

# Configure API key
# Edit .env and set your ANTHROPIC_API_KEY
```

### 2. Seed Demo Data
```bash
python sample_data/seed.py
```

### 3. Run Backend
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 4. Run Frontend
```bash
cd frontend && npm run dev
```

Open http://localhost:5173 to see the dashboard.

## Architecture

```
PDF/DOCX Upload → Ingestion & Parser → Extraction LLM (Claude)
    → ChromaDB + SQLite → Cross-Document Mapping (hybrid retrieval)
    → Risk Detection (rule + LLM) → Prioritization → Alerts
    → React Dashboard with evidence drill-down
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Claude via Anthropic SDK (tool use) |
| Vector DB | ChromaDB (in-process) |
| Graph | NetworkX + JSON export |
| Relational | SQLite + SQLAlchemy |
| Backend | Python 3.11+, FastAPI |
| Frontend | React 18, TypeScript, Vite |
| Styling | Vanilla CSS (dark glassmorphism) |
| Graph Viz | D3.js v7 |

## Non-Negotiable Principles

1. Every output carries a citation to source document + clause/page
2. Extraction (facts) and reasoning (risk judgment) are separate pipeline stages
3. Hybrid retrieval (semantic + BM25), not single-pass summarisation
4. Estimated vs extracted data is visually distinguished everywhere
5. Full audit trail for compliance officer verification
