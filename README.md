# CaseIntel — AI-Powered CCTV Investigation Assistant

CaseIntel is a full-stack forensic investigation platform that transforms raw CCTV surveillance footage into structured, explainable intelligence through a multi-modal AI pipeline.

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────────────────┐
│   React + Vite   │◄───►│             FastAPI Backend                   │
│   Frontend       │     │                                              │
│   (TypeScript)   │     │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│                  │     │  │ YOLOv11  │→ │ByteTrack │→ │ Action    │  │
│  • Dashboard     │     │  │ Detector │  │ Tracker  │  │ Recogn.   │  │
│  • Investigations│     │  └──────────┘  └──────────┘  └───────────┘  │
│  • Video Viewer  │     │       ↓                            ↓        │
│  • Timeline      │     │  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  • Entity Graph  │     │  │ XGBoost  │→ │TreeSHAP  │→ │ LLM Report│  │
│  • Incident      │     │  │Classifier│  │Explainer │  │ Generator │  │
│  • Evidence      │     │  └──────────┘  └──────────┘  └───────────┘  │
│  • Reports       │     │       ↓                                     │
│                  │     │  ┌──────────────────────────────────────┐    │
│                  │     │  │ Neo4j Knowledge Graph / In-Memory    │    │
│                  │     │  └──────────────────────────────────────┘    │
└─────────────────┘     └──────────────────────────────────────────────┘
                              │
                        ┌─────┴─────┐
                        │  SQLite   │
                        │ Database  │
                        └───────────┘
```

## AI Pipeline

| Stage | Technology | Purpose |
|---|---|---|
| Object Detection | YOLOv11n (Ultralytics) | Frame-by-frame person/vehicle/object detection |
| Multi-Object Tracking | ByteTrack (Kalman Filter) | Persistent entity IDs across frames |
| OCR | EasyOCR | Embedded CCTV timestamp extraction |
| Action Recognition | Kinematic Motion Vectors | Behavioral classification (loitering, running, etc.) |
| Temporal Activity | R(2+1)D-18 (PyTorch) | Direct video-level activity recognition |
| Incident Classification | XGBoost 1.8 | Security incident type & severity prediction |
| Explainability | TreeSHAP | Feature contribution analysis for transparency |
| Knowledge Graph | Neo4j / In-Memory Fallback | Entity-relationship topology visualization |
| Report Generation | OpenAI / Ollama / Synthesis Engine | Formal investigation report compilation |

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- (Optional) Neo4j 5.x for persistent knowledge graph

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

### Frontend
```bash
npm install
npm run dev
```

The frontend dev server runs on `http://localhost:5173` and connects to the backend on `http://127.0.0.1:8000`.

## Project Structure

```
Caseintel/
├── src/                    # React frontend (TypeScript)
│   ├── api/               # Typed API client wrappers
│   ├── components/        # Reusable UI components
│   ├── context/           # React Context (state management)
│   ├── pages/             # Page components (routes)
│   ├── types/             # TypeScript type definitions
│   └── utils/             # Utility functions
├── backend/               # FastAPI backend (Python)
│   ├── api/               # API route handlers
│   ├── models/            # SQLAlchemy ORM + Pydantic schemas + ML models
│   ├── services/          # Business logic services
│   ├── uploads/           # Uploaded CCTV footage (gitignored)
│   └── main.py            # Application entry point
```

## Key Design Principles

- **Zero mock data** — All investigation data is derived from real CCTV analysis
- **Explainable AI** — Every classification includes TreeSHAP feature attributions
- **Forensic integrity** — SHA-256 hashing for evidence chain of custody
- **Graceful degradation** — Neo4j falls back to in-memory graph; LLM falls back to synthesis engine
