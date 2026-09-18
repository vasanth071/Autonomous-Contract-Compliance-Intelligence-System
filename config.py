"""
CCIS Configuration — reads from .env file.
All pipeline weight defaults and paths are centralised here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = "claude-sonnet-4-5"

# ── Storage paths ─────────────────────────────────────────────────────────────
CHROMA_PATH: str = os.getenv("CHROMA_PATH", "./data/chroma")
DB_PATH: str = os.getenv("DB_PATH", "./data/ccis.db")
GRAPH_EXPORT_PATH: str = os.getenv("GRAPH_EXPORT_PATH", "./data/graph.json")

# ── Prioritisation weights (must sum ≤ 1.0 — remainder is tolerance) ─────────
W_FINANCIAL: float = float(os.getenv("W_FINANCIAL", "0.35"))
W_REGULATORY: float = float(os.getenv("W_REGULATORY", "0.30"))
W_DEADLINE: float = float(os.getenv("W_DEADLINE", "0.25"))
W_COUNTERPARTY: float = float(os.getenv("W_COUNTERPARTY", "0.10"))

# ── Chunking parameters ───────────────────────────────────────────────────────
MAX_CHUNK_TOKENS: int = 512
OVERLAP_TOKENS: int = 50

# ── Retrieval parameters ──────────────────────────────────────────────────────
SEMANTIC_TOP_K: int = 10
BM25_TOP_K: int = 10

# ── Risk thresholds ───────────────────────────────────────────────────────────
DEADLINE_WARN_DAYS: int = 30
