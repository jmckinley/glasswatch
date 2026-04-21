"""
Create all database tables from SQLAlchemy models.
Bypasses Alembic for initial setup when migration chain has issues.

Usage:
    PYTHONPATH=/home/node/glasswatch DATABASE_URL="postgresql://..." python3 backend/scripts/create_tables.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from backend.db.base import Base
import backend.db.models  # noqa: F401 — register all models

def main():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    # Normalize to sync driver
    if "asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Use psycopg2 sync driver
    sync_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    
    print(f"Connecting to: {sync_url.split('@')[1] if '@' in sync_url else 'configured'}")
    engine = create_engine(sync_url)
    
    print("Creating all tables...")
    Base.metadata.create_all(engine, checkfirst=True)
    
    # Also stamp alembic to latest
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(Path(__file__).parent.parent / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
    
    try:
        command.stamp(alembic_cfg, "007_add_performance_indexes")
        print("Stamped alembic version to 007_add_performance_indexes (head)")
    except Exception as e:
        print(f"Warning: Could not stamp alembic version: {e}")
    
    # List created tables
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nCreated {len(tables)} tables:")
    for t in sorted(tables):
        print(f"  - {t}")
    
    engine.dispose()
    print("\nDone!")

if __name__ == "__main__":
    main()
