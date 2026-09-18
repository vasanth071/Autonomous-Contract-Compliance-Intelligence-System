"""
CCIS Knowledge — ChromaDB vector store wrapper.

Collections: obligations_vec, requirements_vec.
Methods: upsert(), query_similar(text, n).
"""
import chromadb
from chromadb.config import Settings
from typing import Dict, List, Optional

from backend.config import CHROMA_PATH


class VectorStore:
    """Thin wrapper around ChromaDB for obligation / requirement embeddings."""

    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self._obligations = self._client.get_or_create_collection(
            name="obligations_vec",
            metadata={"hnsw:space": "cosine"},
        )
        self._requirements = self._client.get_or_create_collection(
            name="requirements_vec",
            metadata={"hnsw:space": "cosine"},
        )

    # ── Upsert ────────────────────────────────────────────────────────────────

    def upsert_obligation(self, obl_id: str, text: str, metadata: Optional[Dict] = None):
        meta = metadata or {}
        # ChromaDB requires all metadata values to be str, int, float, or bool
        safe_meta = {k: str(v) if v is not None else "" for k, v in meta.items()}
        self._obligations.upsert(
            ids=[obl_id],
            documents=[text],
            metadatas=[safe_meta],
        )

    def upsert_requirement(self, req_id: str, text: str, metadata: Optional[Dict] = None):
        meta = metadata or {}
        safe_meta = {k: str(v) if v is not None else "" for k, v in meta.items()}
        self._requirements.upsert(
            ids=[req_id],
            documents=[text],
            metadatas=[safe_meta],
        )

    # ── Query ─────────────────────────────────────────────────────────────────

    def query_similar_requirements(self, text: str, n: int = 10) -> List[Dict]:
        """Semantic search for requirements similar to the given text."""
        if self._requirements.count() == 0:
            return []
        results = self._requirements.query(
            query_texts=[text],
            n_results=min(n, self._requirements.count()),
        )
        return self._format_results(results)

    def query_similar_obligations(self, text: str, n: int = 10) -> List[Dict]:
        """Semantic search for obligations similar to the given text."""
        if self._obligations.count() == 0:
            return []
        results = self._obligations.query(
            query_texts=[text],
            n_results=min(n, self._obligations.count()),
        )
        return self._format_results(results)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _format_results(results: Dict) -> List[Dict]:
        formatted = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        for i, id_ in enumerate(ids):
            formatted.append({
                "id": id_,
                "text": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else 1.0,
            })
        return formatted

    def get_all_requirement_texts(self) -> List[Dict]:
        """Return all requirement texts for BM25 indexing."""
        if self._requirements.count() == 0:
            return []
        results = self._requirements.get()
        out = []
        for i, id_ in enumerate(results["ids"]):
            out.append({
                "id": id_,
                "text": results["documents"][i],
                "metadata": results["metadatas"][i] if results.get("metadatas") else {},
            })
        return out
