"""
CaseIntel — SQLAlchemy ORM Models
Defines tables for Investigation, Event, Evidence, Video, Entity, and Location.
"""

from sqlalchemy import Column, String, Float, Integer, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class LocationModel(Base):
    __tablename__ = "locations"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)


class InvestigationModel(Base):
    __tablename__ = "investigations"

    id = Column(String(64), primary_key=True, index=True)
    case_number = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(32), default="under_investigation")
    incident_type = Column(String(128), nullable=False)
    severity = Column(String(32), default="HIGH")
    confidence = Column(Float, default=85.0)
    location = Column(String(255), nullable=False)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=True)
    investigator = Column(String(128), default="Unassigned")
    video_count = Column(Integer, default=1)
    duration_analyzed = Column(String(32), default="00:00:00")
    ai_insight = Column(Text, nullable=True)
    incident_data = Column(JSON, nullable=True)
    active_video_id = Column(String(64), nullable=True)

    # Relationships
    events = relationship("EventModel", back_populates="investigation", cascade="all, delete-orphan")
    evidence = relationship("EvidenceModel", back_populates="investigation", cascade="all, delete-orphan")
    entities = relationship("EntityModel", back_populates="investigation", cascade="all, delete-orphan")
    videos = relationship("VideoModel", back_populates="investigation", cascade="all, delete-orphan")


class EventModel(Base):
    __tablename__ = "events"

    id = Column(String(64), primary_key=True, index=True)
    investigation_id = Column(String(64), ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False)
    video_id = Column(String(64), nullable=True, index=True)
    timestamp = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    entity_type = Column(String(32), nullable=False)
    action = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    camera_id = Column(String(64), nullable=False)
    confidence = Column(Float, default=90.0)
    evidence_id = Column(String(64), nullable=True)
    is_suspicious = Column(Boolean, default=False)
    description = Column(Text, nullable=False)
    related_entity_id = Column(String(64), nullable=True)

    investigation = relationship("InvestigationModel", back_populates="events")


class EvidenceModel(Base):
    __tablename__ = "evidence"

    id = Column(String(64), primary_key=True, index=True)
    investigation_id = Column(String(64), ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False)
    video_id = Column(String(64), nullable=True, index=True)
    timestamp = Column(String(64), nullable=False)
    camera_id = Column(String(64), nullable=False)
    type = Column(String(128), nullable=False)
    primary_entity_id = Column(String(64), nullable=False)
    secondary_entity_id = Column(String(64), nullable=True)
    confidence = Column(Float, default=90.0)
    event_id = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    is_key_evidence = Column(Boolean, default=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(String(64), nullable=False)

    investigation = relationship("InvestigationModel", back_populates="evidence")


class VideoModel(Base):
    __tablename__ = "videos"

    id = Column(String(64), primary_key=True, index=True)
    investigation_id = Column(String(64), ForeignKey("investigations.id", ondelete="SET NULL"), index=True, nullable=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    camera_id = Column(String(64), default="C-01")
    location = Column(String(255), default="Unknown Location")
    status = Column(String(32), default="uploaded")
    uploaded_at = Column(String(64), nullable=False)

    investigation = relationship("InvestigationModel", back_populates="videos")


class EntityModel(Base):
    __tablename__ = "entities"

    id = Column(String(64), primary_key=True, index=True)
    investigation_id = Column(String(64), ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False)
    video_id = Column(String(64), nullable=True, index=True)
    type = Column(String(32), nullable=False)
    label = Column(String(128), nullable=False)
    confidence = Column(Float, default=90.0)
    first_seen = Column(String(64), nullable=True)
    last_seen = Column(String(64), nullable=True)
    track_duration = Column(String(32), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    investigation = relationship("InvestigationModel", back_populates="entities")
