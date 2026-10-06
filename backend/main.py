"""
CaseIntel — FastAPI Backend
Entry point for the investigation API server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from api import investigations, videos, events, entities, knowledge_graph, incidents, reports, evidence, notifications
from init_db import init_and_seed_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs DB init on startup."""
    init_and_seed_db()
    yield


app = FastAPI(
    title="CaseIntel API",
    description="AI-Powered CCTV Investigation Assistant — Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(investigations.router, prefix="/api/investigations", tags=["Investigations"])
app.include_router(videos.router,         prefix="/api/videos",         tags=["Videos"])
app.include_router(events.router,         prefix="/api/events",         tags=["Events"])
app.include_router(entities.router,       prefix="/api/entities",       tags=["Entities"])
app.include_router(evidence.router,       prefix="/api/evidence",       tags=["Evidence"])
app.include_router(knowledge_graph.router,prefix="/api/knowledge-graph",tags=["Knowledge Graph"])
app.include_router(incidents.router,      prefix="/api/incidents",      tags=["Incidents"])
app.include_router(reports.router,        prefix="/api/reports",        tags=["Reports"])
app.include_router(notifications.router,  prefix="/api/notifications",  tags=["Notifications"])

@app.get("/")
def root():
    return {
        "system": "CaseIntel",
        "version": "1.0.0-production",
        "status": "operational",
        "mode": "live",
        "ai_pipeline": {
            "yolo_detector": "YOLOv11n (Ultralytics)",
            "tracker": "ByteTrack (Kalman Filter)",
            "action_recognition": "Kinematic Motion Vectors",
            "incident_classifier": "XGBoost 1.8 Classifier",
            "explainability": "TreeSHAP Explainer",
            "knowledge_graph": "Neo4j / Dynamic Cypher Topology",
            "report_generator": "LLM Intelligence Synthesis Engine",
        },
    }


@app.get("/api/health")
def health():
    """Health check that probes actual service readiness instead of returning static values."""
    def _probe(name: str, check_fn) -> str:
        try:
            return "online" if check_fn() else "degraded"
        except Exception:
            return "offline"

    services = {
        "yolo_detector": _probe("yolo", lambda: __import__("os").path.exists(
            __import__("os").path.join(__import__("os").path.dirname(__file__), "models", "yolo11n.pt")
        )),
        "xgboost_classifier": _probe("xgboost", lambda: __import__("os").path.exists(
            __import__("os").path.join(__import__("os").path.dirname(__file__), "models", "xgboost_incident_model.json")
        )),
        "temporal_model": _probe("temporal", lambda: __import__("os").path.exists(
            __import__("os").path.join(__import__("os").path.dirname(__file__), "models", "temporal_surveillance_head.pt")
        )),
        "knowledge_graph": _probe("neo4j", lambda: (
            hasattr(knowledge_graph, "kg_service") and
            getattr(knowledge_graph.kg_service, "is_connected", False)
        )),
        "database": _probe("db", lambda: (
            engine.connect().close() or True
        )),
    }

    all_online = all(s == "online" for s in services.values())
    any_offline = any(s == "offline" for s in services.values())

    return {
        "status": "healthy" if all_online else ("degraded" if not any_offline else "unhealthy"),
        "mode": "live",
        "services": services,
    }

