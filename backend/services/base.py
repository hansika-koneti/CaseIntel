"""CaseIntel — Abstract service base classes"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class VideoAnalyzerService(ABC):
    """Abstract video analysis pipeline."""

    @abstractmethod
    def analyze(self, video_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run full pipeline on video. Returns detected entities, events, and evidence."""
        ...

    @abstractmethod
    def get_status(self, video_id: str) -> Dict[str, Any]:
        """Get current processing status."""
        ...


class IncidentClassifierService(ABC):
    """Abstract incident classification service."""

    @abstractmethod
    def classify(self, events: List[Dict], entities: List[Dict]) -> Dict[str, Any]:
        """Classify incident from extracted events and entities."""
        ...


class ReportGeneratorService(ABC):
    """Abstract report generation service."""

    @abstractmethod
    def generate(self, investigation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate investigation report from full investigation data."""
        ...


class KnowledgeGraphService(ABC):
    """Abstract knowledge graph service."""

    @abstractmethod
    def build(self, events: List[Dict], entities: List[Dict]) -> Dict[str, Any]:
        """Build knowledge graph from events and entities."""
        ...

    @abstractmethod
    def query(self, investigation_id: str) -> Dict[str, Any]:
        """Query knowledge graph for an investigation."""
        ...


class ActionRecognitionBaseService(ABC):
    """Abstract action recognition service interface."""

    @abstractmethod
    def classify_actions(
        self,
        tracks: List[Dict[str, Any]],
        video_metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Classify actions per track across temporal intervals."""
        ...


import re
from typing import Optional

def normalize_location_name(loc: Optional[str]) -> str:
    """Normalize raw or typo-prone location inputs to professional investigator labels."""
    if not loc:
        return "Monitored Zone"
    loc_str = str(loc).strip()
    if loc_str.lower() in ["", "none", "null", "undefined", "location not specified", "unknown", "unknown location"]:
        return "Monitored Zone"

    # Handle known test typos or slugs
    cleaned = re.sub(r'newp+lace', 'New Place', loc_str, flags=re.IGNORECASE)
    if cleaned.lower() in ["newplace", "new place"]:
        return "New Place"
    if cleaned.lower() == "house":
        return "House (Premises)"
    if cleaned.lower() == "new":
        return "New Sector"
    if cleaned.lower() == "monitored zone":
        return "Monitored Zone"

    # Split camelCase e.g. RoomB -> Room B, WestGate -> West Gate
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    # Replace underscores and hyphens with spaces
    cleaned = re.sub(r'[_-]+', ' ', cleaned)
    # Capitalize words cleanly
    words = [w.capitalize() if not w.isupper() else w for w in cleaned.split()]
    return " ".join(words)

