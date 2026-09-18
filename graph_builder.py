"""
CCIS Mapping — Cross-document graph builder.

Hybrid retrieval (semantic + BM25 keyword) → Claude LLM reasoning → NetworkX graph.
Also checks requirement↔requirement pairs for internal policy conflicts.
"""
import json
import uuid
import hashlib
from typing import List, Dict

import networkx as nx
from rank_bm25 import BM25Okapi
from anthropic import Anthropic

from backend.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SEMANTIC_TOP_K, BM25_TOP_K, GRAPH_EXPORT_PATH
from backend.database import (
    SessionLocal, ObligationModel, RequirementModel, RelationshipModel, AuditLogModel
)
from backend.knowledge.vector_store import VectorStore
from backend.extraction.prompts import (
    SYSTEM_PROMPT, RELATIONSHIP_CLASSIFICATION_PROMPT, RELATIONSHIP_TOOL
)
from backend.alerts.audit import log_audit

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_anthropic_api_key_here" else None


def build_mappings(doc_id: str) -> List[Dict]:
    """
    For each obligation in the given document, run hybrid retrieval against
    all requirements and classify the relationship using Claude.
    Also checks requirement↔requirement pairs for policy_conflict.
    """
    db = SessionLocal()
    vs = VectorStore()
    relationships: List[Dict] = []

    try:
        obligations = db.query(ObligationModel).filter(
            ObligationModel.doc_id == doc_id
        ).all()

        # Get all requirement texts for BM25
        all_req_texts = vs.get_all_requirement_texts()
        bm25_corpus = [r["text"].lower().split() for r in all_req_texts] if all_req_texts else []
        bm25 = BM25Okapi(bm25_corpus) if bm25_corpus else None

        for obl in obligations:
            obl_text = obl.statement
            obl_evidence = json.loads(obl.source_evidence) if obl.source_evidence else {}

            # ── Hybrid retrieval ──────────────────────────────────────────
            # 1. Semantic pass
            semantic_results = vs.query_similar_requirements(obl_text, n=SEMANTIC_TOP_K)

            # 2. BM25 keyword pass
            bm25_results = []
            if bm25 and bm25_corpus:
                scores = bm25.get_scores(obl_text.lower().split())
                scored = list(zip(all_req_texts, scores))
                scored.sort(key=lambda x: x[1], reverse=True)
                bm25_results = [
                    {"id": item["id"], "text": item["text"], "metadata": item.get("metadata", {})}
                    for item, score in scored[:BM25_TOP_K]
                    if score > 0
                ]

            # 3. Merge & de-duplicate
            seen_ids = set()
            candidates = []
            for r in semantic_results + bm25_results:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    candidates.append(r)

            # ── Classify each pair ────────────────────────────────────────
            for candidate in candidates:
                req = db.query(RequirementModel).filter(
                    RequirementModel.requirement_id == candidate["id"]
                ).first()
                if not req:
                    continue

                req_evidence = json.loads(req.source_evidence) if req.source_evidence else {}

                rel = _classify_relationship(
                    obl_text, obl.doc_id, obl_evidence.get("clause_id", "N/A"),
                    req.rule, req.doc_id, req_evidence.get("clause_id", "N/A"),
                )
                if not rel or rel.get("edge_type") == "unaddressed":
                    continue

                rel_id = str(uuid.uuid4())
                rel_model = RelationshipModel(
                    relationship_id=rel_id,
                    obligation_id=obl.obligation_id,
                    requirement_id=req.requirement_id,
                    edge_type=rel["edge_type"],
                    confidence=rel.get("confidence", 0.5),
                    explanation=rel.get("explanation"),
                    evidence_a=rel.get("evidence_a"),
                    evidence_b=rel.get("evidence_b"),
                )
                db.add(rel_model)

                audit = AuditLogModel(
                    log_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    stage="map",
                    entity_id=rel_id,
                    output_json=json.dumps(rel, default=str),
                    model_reasoning=rel.get("explanation", ""),
                )
                db.add(audit)

                relationships.append({**rel, "relationship_id": rel_id})

        # ── Requirement ↔ Requirement policy_conflict check ───────────────
        all_requirements = db.query(RequirementModel).all()
        if len(all_requirements) > 1:
            for i, req_a in enumerate(all_requirements):
                for req_b in all_requirements[i + 1:]:
                    if req_a.doc_id == req_b.doc_id:
                        continue  # same doc — skip

                    ev_a = json.loads(req_a.source_evidence) if req_a.source_evidence else {}
                    ev_b = json.loads(req_b.source_evidence) if req_b.source_evidence else {}

                    rel = _classify_relationship(
                        req_a.rule, req_a.doc_id, ev_a.get("clause_id", "N/A"),
                        req_b.rule, req_b.doc_id, ev_b.get("clause_id", "N/A"),
                        is_policy_pair=True,
                    )
                    if rel and rel.get("edge_type") in ("conflicts", "policy_conflict"):
                        rel_id = str(uuid.uuid4())
                        rel_model = RelationshipModel(
                            relationship_id=rel_id,
                            obligation_id=req_a.requirement_id,  # repurposed for req-req
                            requirement_id=req_b.requirement_id,
                            edge_type="policy_conflict",
                            confidence=rel.get("confidence", 0.5),
                            explanation=rel.get("explanation"),
                            evidence_a=rel.get("evidence_a"),
                            evidence_b=rel.get("evidence_b"),
                        )
                        db.add(rel_model)
                        relationships.append({**rel, "relationship_id": rel_id})

        db.commit()

        # ── Export graph as JSON ──────────────────────────────────────────
        _export_graph(db)

    finally:
        db.close()

    return relationships


def _classify_relationship(
    text_a: str, doc_a: str, clause_a: str,
    text_b: str, doc_b: str, clause_b: str,
    is_policy_pair: bool = False,
) -> Dict:
    """Use Claude to classify the relationship between two texts."""
    if client is None:
        return {}

    prompt = RELATIONSHIP_CLASSIFICATION_PROMPT.format(
        obl_doc_id=doc_a, obl_clause=clause_a, obligation_text=text_a,
        req_doc_id=doc_b, req_clause=clause_b, requirement_text=text_b,
    )
    if is_policy_pair:
        prompt += "\n\nNOTE: Both texts are policy requirements. Use 'policy_conflict' if they contradict each other."

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=[RELATIONSHIP_TOOL],
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "classify_relationship":
                return block.input
    except Exception as e:
        print(f"[CCIS] Relationship classification error: {e}")

    return {}


def _export_graph(db):
    """Build and export the full relationship graph as JSON."""
    import os
    G = nx.DiGraph()

    obligations = db.query(ObligationModel).all()
    requirements = db.query(RequirementModel).all()
    rels = db.query(RelationshipModel).all()

    for obl in obligations:
        G.add_node(obl.obligation_id, label=obl.statement[:80], node_type="obligation", doc_id=obl.doc_id)
    for req in requirements:
        G.add_node(req.requirement_id, label=req.rule[:80], node_type="requirement", doc_id=req.doc_id)
    for r in rels:
        G.add_edge(r.obligation_id, r.requirement_id,
                    edge_type=r.edge_type, confidence=r.confidence,
                    explanation=r.explanation)

    graph_data = {
        "nodes": [
            {"id": n, **G.nodes[n]} for n in G.nodes
        ],
        "edges": [
            {"source": u, "target": v, **G.edges[u, v]} for u, v in G.edges
        ],
    }

    os.makedirs(os.path.dirname(GRAPH_EXPORT_PATH) if os.path.dirname(GRAPH_EXPORT_PATH) else ".", exist_ok=True)
    with open(GRAPH_EXPORT_PATH, "w") as f:
        json.dump(graph_data, f, indent=2, default=str)


def get_graph_data() -> Dict:
    """Read the exported graph JSON."""
    import os
    if not os.path.exists(GRAPH_EXPORT_PATH):
        return {"nodes": [], "edges": []}
    with open(GRAPH_EXPORT_PATH, "r") as f:
        return json.load(f)
