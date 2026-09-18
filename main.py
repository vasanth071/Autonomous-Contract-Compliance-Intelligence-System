"""
CCIS Backend — FastAPI Entrypoint
Mounts all routers and enables CORS for the Vite dev server.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.ingestion.router import router as ingestion_router
from backend.mapping.router import router as mapping_router
from backend.risk.router import router as risk_router
from backend.alerts.router import router as alerts_router

app = FastAPI(
    title="Contract–Compliance Intelligence System (CCIS)",
    description="Evidence-backed AI pipeline for contract compliance analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router, prefix="/api")
app.include_router(mapping_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    init_db()
    os.makedirs("data/chroma", exist_ok=True)
    os.makedirs("data", exist_ok=True)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "CCIS"}
