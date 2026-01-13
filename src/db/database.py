"""
Geoff OS - Database Layer

SQLite-based persistent storage for:
- Entities (projects, people, clients, tasks)
- Relationships between entities
- Jobs and execution history
- Learnings and preferences

This provides structured querying alongside the markdown files.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "geoff.db"


def get_connection() -> sqlite3.Connection:
    """Get database connection with row factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session():
    """Context manager for database sessions."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database schema."""
    with db_session() as conn:
        conn.executescript(SCHEMA)
    print(f"Database initialized at {DB_PATH}")


# --- Schema ---

SCHEMA = """
-- Entities: Projects, People, Clients, Tasks
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- project, person, client, task, decision
    name TEXT NOT NULL,
    status TEXT,
    priority TEXT,
    content TEXT,  -- Full markdown content
    metadata TEXT,  -- JSON metadata
    file_path TEXT,  -- Source markdown file
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_synced_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);

-- Relationships between entities
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity_id TEXT NOT NULL,
    to_entity_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,  -- works_on, manages, stakeholder_of, blocked_by, etc.
    metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_entity_id) REFERENCES entities(id),
    FOREIGN KEY (to_entity_id) REFERENCES entities(id),
    UNIQUE(from_entity_id, to_entity_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_rel_to ON relationships(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(relationship_type);

-- Jobs: Execution history
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    intent TEXT NOT NULL,  -- brief, prep, task, draft, status, query
    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
    source TEXT,  -- telegram, cli, scheduler
    inputs TEXT,  -- JSON
    outputs TEXT,  -- JSON (artefact paths, results)
    context_used TEXT,  -- JSON (which knowledge files were used)
    duration_ms INTEGER,
    error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_intent ON jobs(intent);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);

-- Learnings: Extracted knowledge
CREATE TABLE IF NOT EXISTS learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,  -- preference, correction, pattern, insight
    category TEXT,  -- communication, workflow, person, project
    content TEXT NOT NULL,
    source TEXT,  -- What triggered this learning
    confidence TEXT DEFAULT 'medium',  -- low, medium, high
    applied_count INTEGER DEFAULT 0,  -- How many times used
    processed INTEGER DEFAULT 0,  -- Has this been consolidated?
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_applied_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_learnings_type ON learnings(type);
CREATE INDEX IF NOT EXISTS idx_learnings_category ON learnings(category);
CREATE INDEX IF NOT EXISTS idx_learnings_processed ON learnings(processed);

-- Preferences: User preferences (distilled from learnings)
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,  -- communication, format, workflow, timing
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    context TEXT,  -- When this preference applies
    source TEXT,  -- Where this was learned
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, key, context)
);

CREATE INDEX IF NOT EXISTS idx_prefs_category ON preferences(category);

-- Interactions: Conversation history (for context)
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    role TEXT NOT NULL,  -- user, assistant
    content TEXT NOT NULL,
    entities_mentioned TEXT,  -- JSON array of entity IDs
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_interactions_job ON interactions(job_id);

-- Full-text search virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    name,
    content,
    content='entities',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
    INSERT INTO entities_fts(rowid, name, content) VALUES (new.rowid, new.name, new.content);
END;

CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
    INSERT INTO entities_fts(entities_fts, rowid, name, content) VALUES('delete', old.rowid, old.name, old.content);
END;

CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
    INSERT INTO entities_fts(entities_fts, rowid, name, content) VALUES('delete', old.rowid, old.name, old.content);
    INSERT INTO entities_fts(rowid, name, content) VALUES (new.rowid, new.name, new.content);
END;
"""


# --- Data Classes ---

@dataclass
class Entity:
    id: str
    type: str
    name: str
    status: Optional[str] = None
    priority: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict] = None
    file_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Relationship:
    from_entity_id: str
    to_entity_id: str
    relationship_type: str
    metadata: Optional[Dict] = None


@dataclass
class Job:
    id: str
    intent: str
    status: str = "pending"
    source: Optional[str] = None
    inputs: Optional[Dict] = None
    outputs: Optional[Dict] = None
    context_used: Optional[List[str]] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Learning:
    type: str
    content: str
    category: Optional[str] = None
    source: Optional[str] = None
    confidence: str = "medium"


# --- Repository Classes ---

class EntityRepository:
    """CRUD operations for entities."""

    @staticmethod
    def create(entity: Entity) -> str:
        with db_session() as conn:
            conn.execute("""
                INSERT INTO entities (id, type, name, status, priority, content, metadata, file_path, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entity.id,
                entity.type,
                entity.name,
                entity.status,
                entity.priority,
                entity.content,
                json.dumps(entity.metadata) if entity.metadata else None,
                entity.file_path,
                datetime.now().isoformat()
            ))
        return entity.id

    @staticmethod
    def get(entity_id: str) -> Optional[Entity]:
        with db_session() as conn:
            row = conn.execute(
                "SELECT * FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()
            if row:
                return Entity(
                    id=row["id"],
                    type=row["type"],
                    name=row["name"],
                    status=row["status"],
                    priority=row["priority"],
                    content=row["content"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                    file_path=row["file_path"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
        return None

    @staticmethod
    def get_by_type(entity_type: str) -> List[Entity]:
        with db_session() as conn:
            rows = conn.execute(
                "SELECT * FROM entities WHERE type = ? ORDER BY updated_at DESC",
                (entity_type,)
            ).fetchall()
            return [Entity(
                id=row["id"],
                type=row["type"],
                name=row["name"],
                status=row["status"],
                priority=row["priority"],
                content=row["content"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
                file_path=row["file_path"]
            ) for row in rows]

    @staticmethod
    def search(query: str, entity_type: Optional[str] = None) -> List[Entity]:
        """Full-text search across entities."""
        with db_session() as conn:
            if entity_type:
                rows = conn.execute("""
                    SELECT e.* FROM entities e
                    JOIN entities_fts fts ON e.rowid = fts.rowid
                    WHERE entities_fts MATCH ? AND e.type = ?
                    ORDER BY rank
                    LIMIT 20
                """, (query, entity_type)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT e.* FROM entities e
                    JOIN entities_fts fts ON e.rowid = fts.rowid
                    WHERE entities_fts MATCH ?
                    ORDER BY rank
                    LIMIT 20
                """, (query,)).fetchall()

            return [Entity(
                id=row["id"],
                type=row["type"],
                name=row["name"],
                status=row["status"],
                priority=row["priority"],
                content=row["content"],
                file_path=row["file_path"]
            ) for row in rows]

    @staticmethod
    def update(entity: Entity):
        with db_session() as conn:
            conn.execute("""
                UPDATE entities
                SET name = ?, status = ?, priority = ?, content = ?,
                    metadata = ?, file_path = ?, updated_at = ?
                WHERE id = ?
            """, (
                entity.name,
                entity.status,
                entity.priority,
                entity.content,
                json.dumps(entity.metadata) if entity.metadata else None,
                entity.file_path,
                datetime.now().isoformat(),
                entity.id
            ))

    @staticmethod
    def delete(entity_id: str):
        with db_session() as conn:
            conn.execute("DELETE FROM entities WHERE id = ?", (entity_id,))


class RelationshipRepository:
    """CRUD operations for relationships."""

    @staticmethod
    def create(rel: Relationship):
        with db_session() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO relationships
                (from_entity_id, to_entity_id, relationship_type, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                rel.from_entity_id,
                rel.to_entity_id,
                rel.relationship_type,
                json.dumps(rel.metadata) if rel.metadata else None
            ))

    @staticmethod
    def get_for_entity(entity_id: str) -> List[Dict]:
        """Get all relationships for an entity."""
        with db_session() as conn:
            rows = conn.execute("""
                SELECT r.*, e.name as related_name, e.type as related_type
                FROM relationships r
                JOIN entities e ON (
                    CASE WHEN r.from_entity_id = ? THEN r.to_entity_id ELSE r.from_entity_id END = e.id
                )
                WHERE r.from_entity_id = ? OR r.to_entity_id = ?
            """, (entity_id, entity_id, entity_id)).fetchall()

            return [{
                "entity_id": entity_id,
                "related_id": row["to_entity_id"] if row["from_entity_id"] == entity_id else row["from_entity_id"],
                "related_name": row["related_name"],
                "related_type": row["related_type"],
                "relationship": row["relationship_type"],
                "direction": "outgoing" if row["from_entity_id"] == entity_id else "incoming"
            } for row in rows]


class JobRepository:
    """CRUD operations for jobs."""

    @staticmethod
    def create(job: Job) -> str:
        with db_session() as conn:
            conn.execute("""
                INSERT INTO jobs (id, intent, status, source, inputs, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.intent,
                job.status,
                job.source,
                json.dumps(job.inputs) if job.inputs else None,
                datetime.now().isoformat()
            ))
        return job.id

    @staticmethod
    def update_status(job_id: str, status: str, outputs: Optional[Dict] = None,
                      context_used: Optional[List[str]] = None,
                      duration_ms: Optional[int] = None,
                      error: Optional[str] = None):
        with db_session() as conn:
            conn.execute("""
                UPDATE jobs
                SET status = ?, outputs = ?, context_used = ?,
                    duration_ms = ?, error = ?, completed_at = ?
                WHERE id = ?
            """, (
                status,
                json.dumps(outputs) if outputs else None,
                json.dumps(context_used) if context_used else None,
                duration_ms,
                error,
                datetime.now().isoformat() if status in ("completed", "failed") else None,
                job_id
            ))

    @staticmethod
    def get_recent(limit: int = 20) -> List[Job]:
        with db_session() as conn:
            rows = conn.execute("""
                SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?
            """, (limit,)).fetchall()

            return [Job(
                id=row["id"],
                intent=row["intent"],
                status=row["status"],
                source=row["source"],
                inputs=json.loads(row["inputs"]) if row["inputs"] else None,
                outputs=json.loads(row["outputs"]) if row["outputs"] else None,
                context_used=json.loads(row["context_used"]) if row["context_used"] else None,
                duration_ms=row["duration_ms"],
                error=row["error"],
                created_at=row["created_at"],
                completed_at=row["completed_at"]
            ) for row in rows]

    @staticmethod
    def get_stats() -> Dict:
        """Get job statistics."""
        with db_session() as conn:
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            by_intent = conn.execute("""
                SELECT intent, COUNT(*) as count
                FROM jobs GROUP BY intent
            """).fetchall()
            by_status = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM jobs GROUP BY status
            """).fetchall()

            return {
                "total": total,
                "by_intent": {row["intent"]: row["count"] for row in by_intent},
                "by_status": {row["status"]: row["count"] for row in by_status}
            }


class LearningRepository:
    """CRUD operations for learnings."""

    @staticmethod
    def create(learning: Learning) -> int:
        with db_session() as conn:
            cursor = conn.execute("""
                INSERT INTO learnings (type, category, content, source, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (
                learning.type,
                learning.category,
                learning.content,
                learning.source,
                learning.confidence
            ))
            return cursor.lastrowid

    @staticmethod
    def get_unprocessed() -> List[Dict]:
        with db_session() as conn:
            rows = conn.execute("""
                SELECT * FROM learnings WHERE processed = 0
                ORDER BY created_at DESC
            """).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def mark_processed(learning_id: int):
        with db_session() as conn:
            conn.execute(
                "UPDATE learnings SET processed = 1 WHERE id = ?",
                (learning_id,)
            )

    @staticmethod
    def increment_applied(learning_id: int):
        with db_session() as conn:
            conn.execute("""
                UPDATE learnings
                SET applied_count = applied_count + 1, last_applied_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), learning_id))


class PreferenceRepository:
    """CRUD operations for preferences."""

    @staticmethod
    def set(category: str, key: str, value: str, context: Optional[str] = None,
            source: Optional[str] = None):
        with db_session() as conn:
            conn.execute("""
                INSERT INTO preferences (category, key, value, context, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(category, key, context) DO UPDATE SET
                    value = excluded.value,
                    source = excluded.source,
                    updated_at = excluded.updated_at
            """, (category, key, value, context, source, datetime.now().isoformat()))

    @staticmethod
    def get(category: str, key: str, context: Optional[str] = None) -> Optional[str]:
        with db_session() as conn:
            if context:
                row = conn.execute("""
                    SELECT value FROM preferences
                    WHERE category = ? AND key = ? AND context = ?
                """, (category, key, context)).fetchone()
            else:
                row = conn.execute("""
                    SELECT value FROM preferences
                    WHERE category = ? AND key = ? AND context IS NULL
                """, (category, key)).fetchone()
            return row["value"] if row else None

    @staticmethod
    def get_all(category: Optional[str] = None) -> List[Dict]:
        with db_session() as conn:
            if category:
                rows = conn.execute("""
                    SELECT * FROM preferences WHERE category = ?
                """, (category,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM preferences").fetchall()
            return [dict(row) for row in rows]


# --- CLI ---

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "init":
            init_database()
        elif cmd == "stats":
            stats = JobRepository.get_stats()
            print(json.dumps(stats, indent=2))
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python database.py [init|stats]")
    else:
        print("Geoff OS Database")
        print(f"Path: {DB_PATH}")
        print("\nCommands:")
        print("  init  - Initialize database schema")
        print("  stats - Show job statistics")
