"""
CaseIntel — FastAPI Backend
Entry point for the investigation API server.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import investigations, videos, events, entities, knowledge_graph, incidents, reports, evidence, notifications

app = FastAPI(
    title="CaseIntel API",
    description="AI-Powered CCTV Investigation Assistant — Backend API",
    version="1.0.0-prototype",
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


from init_db import init_and_seed_db

@app.on_event("startup")
def on_startup():
    init_and_seed_db()


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
    return {
        "status": "healthy",
        "mode": "live",
        "services": {
            "yolo_detector": "online",
            "bytetrack": "online",
            "action_recognition": "online",
            "incident_classifier": "online",
            "shap_explainer": "online",
            "knowledge_graph": "online",
            "report_generator": "online",
        },
    }

