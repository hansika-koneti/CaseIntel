"""
CaseIntel — Database Initializer & Seeder
Creates tables and seeds initial investigation data if database is empty.
"""

import hashlib
from database import engine, SessionLocal, Base
from models.db import (
    InvestigationModel,
    EventModel,
    EvidenceModel,
    EntityModel,
    LocationModel,
)
def init_and_seed_db():
    # Only create database tables — zero mock/seed data
    Base.metadata.create_all(bind=engine)
    try:
        from migrate_video_id import run_migration
        run_migration()
    except Exception as e:
        print(f"Migration check notice: {e}")


if __name__ == "__main__":
    init_and_seed_db()
    print("Database schema verified.")

