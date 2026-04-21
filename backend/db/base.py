"""
Database base class and metadata.

Re-exports Base from base_class for backwards compatibility.
All models should use the same declarative base.
"""
from backend.db.base_class import Base  # noqa: F401
