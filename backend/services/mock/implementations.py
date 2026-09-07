"""
CaseIntel — Mock Service Implementations
Replace these with real YOLOv11, XGBoost, LLM implementations.
"""

import time
from typing import Dict, Any, List
from services.base import VideoAnalyzerService, IncidentClassifierService, ReportGeneratorService, KnowledgeGraphService
from data.sample_data import MOCK_INVESTIGATION, MOCK_KNOWLEDGE_GRAPH


class MockVideoAnalyzer(VideoAnalyzerService):
    """
    Mock video analysis pipeline.
    Replace with: YOLOv11 + ByteTrack + MMAction2 + EasyOCR integration.
    """

    def analyze(self, video_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Replace with real pipeline:
        # 1. Extract frames with OpenCV
        # 2. Run YOLOv11 detection on each frame
        # 3. Apply ByteTrack for multi-object tracking
        # 4. Run MMAction2 for activity recognition
        # 5. Run EasyOCR for timestamp extraction
        # 6. Extract events from tracks + activities
        time.sleep(0.1)  # Simulate processing
        return {
            "video_id": f"vid-{int(time.time())}",
            "status": "completed",
            "entities": MOCK_INVESTIGATION["entities"],
            "events": MOCK_INVESTIGATION["events"],
            "evidence": MOCK_INVESTIGATION["evidence"],
        }

    def get_status(self, video_id: str) -> Dict[str, Any]:
        return {
            "video_id": video_id,
            "status": "completed",
            "pipeline_stages": [
                {"id": "upload",     "label": "Video uploaded",                  "status": "completed", "progress": 100},
                {"id": "frames",     "label": "Frame extraction",                 "status": "completed", "progress": 100},
                {"id": "detection",  "label": "Object detection (YOLOv11)",       "status": "completed", "progress": 100},
                {"id": "tracking",   "label": "Object tracking (ByteTrack)",      "status": "completed", "progress": 100},
                {"id": "activity",   "label": "Activity recognition (MMAction2)", "status": "completed", "progress": 100},
                {"id": "ocr",        "label": "OCR extraction (EasyOCR)",         "status": "completed", "progress": 100},
                {"id": "events",     "label": "Event extraction",                 "status": "completed", "progress": 100},
                {"id": "graph",      "label": "Knowledge graph (Neo4j)",          "status": "completed", "progress": 100},
                {"id": "classify",   "label": "Incident classification (XGBoost)","status": "completed", "progress": 100},
                {"id": "report",     "label": "Report generation (LLM)",          "status": "completed", "progress": 100},
            ],
            "completed_stages": 10,
            "total_stages": 10,
            "result_summary": "Suspicious Activity detected — 87.4% confidence",
        }


class MockIncidentClassifier(IncidentClassifierService):
    """
    Mock incident classifier.
    Replace with: XGBoost model loading + SHAP value computation.
    """

    def classify(self, events: List[Dict], entities: List[Dict]) -> Dict[str, Any]:
        # TODO: Replace with:
        # 1. Feature engineering from events (duration, proximity, etc.)
        # 2. Load trained XGBoost model
        # 3. Run inference → probability scores
        # 4. Compute SHAP values for explainability
        return MOCK_INVESTIGATION["incident"]


class MockReportGenerator(ReportGeneratorService):
    """
    Mock LLM-based report generator.
    Replace with: Ollama or OpenAI API call with structured prompt.
    """

    def generate(self, investigation: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Replace with:
        # 1. Build prompt from investigation data (entities, events, incident)
        # 2. Call ollama.chat() or openai.chat.completions.create()
        # 3. Parse structured response
        # 4. Return formatted report
        return MOCK_INVESTIGATION.get("report", {})


class MockKnowledgeGraphService(KnowledgeGraphService):
    """
    Mock knowledge graph service.
    Replace with: Neo4j driver + Cypher query execution.
    """

    def build(self, events: List[Dict], entities: List[Dict]) -> Dict[str, Any]:
        # TODO: Replace with:
        # 1. Connect to Neo4j
        # 2. Create entity nodes via MERGE
        # 3. Create relationship edges from events
        # 4. Return graph data
        return MOCK_KNOWLEDGE_GRAPH

    def query(self, investigation_id: str) -> Dict[str, Any]:
        # TODO: Replace with Neo4j Cypher MATCH query
        return MOCK_KNOWLEDGE_GRAPH
