"""
CaseIntel — Mock Report Generator Service
Deterministic fallback report generator for unit tests and isolated development.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from services.base import ReportGeneratorService


class MockReportGeneratorService(ReportGeneratorService):
    """Deterministic mock report generator service."""

    def generate(self, investigation: Dict[str, Any]) -> Dict[str, Any]:
        inv_id = investigation.get("id", "inv-001")
        case_num = investigation.get("case_number", "CASE-2026-001")
        loc = investigation.get("location", "Parking Area")
        incident = investigation.get("incident", {})
        inc_type = incident.get("type", "Suspicious Activity")
        conf = incident.get("confidence", 87.4)
        sev = incident.get("severity", "HIGH")

        now_str = datetime.now(timezone.utc).isoformat()

        return {
            "id": f"REP-{inv_id[-6:]}",
            "investigation_id": inv_id,
            "generated_at": now_str,
            "generator_model": "CaseIntel Synthesis Engine (Mock)",
            "executive_summary": (
                f"Automated CCTV investigation report for {case_num} at {loc}. "
                f"The AI pipeline identified a {sev} severity {inc_type} event with {conf}% model confidence. "
                "Immediate follow-up and investigator verification is recommended."
            ),
            "sections": [
                {
                    "id": "sec-1",
                    "title": "Incident Classification & Rationale",
                    "content": f"Classification: {inc_type}\nConfidence: {conf}%\nSeverity: {sev}\nModel: XGBoost + TreeSHAP",
                },
                {
                    "id": "sec-2",
                    "title": "Chronological Narrative & Timeline",
                    "content": "21:31:04 — Subject enters monitored zone.\n21:31:32 — Proximity event observed.\n21:32:05 — Rapid departure detected.",
                },
                {
                    "id": "sec-3",
                    "title": "Key Evidence Summary",
                    "content": "5 chronological events logged with SHA-256 integrity hash verification across CCTV Camera C-01.",
                },
                {
                    "id": "sec-4",
                    "title": "Recommendations & Next Steps",
                    "content": "1. Dispatch security patrol to inspect zone.\n2. Cross-reference vehicle registration.\n3. Preserve primary CCTV archive.",
                },
            ],
            "disclaimer": "This report was generated with AI assistance and must be independently reviewed by authorized personnel.",
        }
