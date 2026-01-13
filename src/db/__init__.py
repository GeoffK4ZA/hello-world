"""
Geoff OS - Database Layer

Components:
- database: SQLite schema and repositories
- sync: Markdown <-> SQLite synchronization
"""

from .database import (
    Entity, Relationship, Job, Learning,
    EntityRepository, RelationshipRepository, JobRepository,
    LearningRepository, PreferenceRepository,
    init_database, db_session, DB_PATH
)
from .sync import sync_knowledge_base, sync_file_to_db, sync_db_to_file

__all__ = [
    'Entity', 'Relationship', 'Job', 'Learning',
    'EntityRepository', 'RelationshipRepository', 'JobRepository',
    'LearningRepository', 'PreferenceRepository',
    'init_database', 'db_session', 'DB_PATH',
    'sync_knowledge_base', 'sync_file_to_db', 'sync_db_to_file'
]
