"""
Geoff OS - Knowledge Base Indexer

Full indexing pipeline that:
1. Syncs markdown files to SQLite (structured data + FTS)
2. Creates vector embeddings in ChromaDB (semantic search)
3. Extracts relationships between entities

Run this after adding new knowledge files or periodically.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from db.database import init_database, DB_PATH
from db.sync import sync_knowledge_base, KNOWLEDGE_PATH

try:
    from rag.embeddings import EmbeddingStore, index_knowledge_base, CHROMADB_AVAILABLE
except ImportError:
    CHROMADB_AVAILABLE = False


def run_full_index(include_vectors: bool = True) -> Dict:
    """
    Run full indexing pipeline.

    Args:
        include_vectors: Whether to create vector embeddings (requires ChromaDB)

    Returns:
        Statistics about indexing
    """
    stats = {
        "started_at": datetime.now().isoformat(),
        "sqlite": {},
        "vectors": {},
        "status": "success"
    }

    print("=" * 50)
    print("Geoff OS - Knowledge Base Indexer")
    print("=" * 50)

    # Step 1: Initialize SQLite
    print("\n[1/3] Initializing SQLite database...")
    try:
        init_database()
        print(f"  Database: {DB_PATH}")
    except Exception as e:
        print(f"  Error: {e}")
        stats["status"] = "partial"

    # Step 2: Sync markdown to SQLite
    print("\n[2/3] Syncing knowledge base to SQLite...")
    try:
        sync_stats = sync_knowledge_base()
        stats["sqlite"] = sync_stats
        print(f"  Synced: {sync_stats['synced']} files")
        print(f"  Skipped: {sync_stats['skipped']} files")
        if sync_stats['errors'] > 0:
            print(f"  Errors: {sync_stats['errors']}")
    except Exception as e:
        print(f"  Error: {e}")
        stats["sqlite"] = {"error": str(e)}
        stats["status"] = "partial"

    # Step 3: Create vector embeddings
    if include_vectors and CHROMADB_AVAILABLE:
        print("\n[3/3] Creating vector embeddings...")
        try:
            store = EmbeddingStore()
            vector_stats = index_knowledge_base(store)
            stats["vectors"] = vector_stats
            print(f"  Indexed: {vector_stats['indexed']} documents")
            print(f"  Skipped: {vector_stats['skipped']} documents")
            if vector_stats['errors'] > 0:
                print(f"  Errors: {vector_stats['errors']}")
        except Exception as e:
            print(f"  Error: {e}")
            stats["vectors"] = {"error": str(e)}
            stats["status"] = "partial"
    elif include_vectors:
        print("\n[3/3] Skipping vector embeddings (ChromaDB not installed)")
        stats["vectors"] = {"skipped": "ChromaDB not installed"}
    else:
        print("\n[3/3] Skipping vector embeddings (disabled)")
        stats["vectors"] = {"skipped": "disabled"}

    # Summary
    stats["completed_at"] = datetime.now().isoformat()

    print("\n" + "=" * 50)
    print("Indexing Complete")
    print("=" * 50)
    print(f"\nKnowledge path: {KNOWLEDGE_PATH}")
    print(f"Database path: {DB_PATH}")
    if CHROMADB_AVAILABLE:
        print(f"Vector store: {Path(__file__).parent.parent / 'data' / 'chroma'}")

    return stats


def quick_sync() -> Dict:
    """Quick sync without vector embeddings."""
    return run_full_index(include_vectors=False)


def watch_and_sync(interval_seconds: int = 60):
    """
    Watch knowledge directory and sync on changes.

    Note: Requires watchdog package for file watching.
    Falls back to polling if not available.
    """
    import time

    print(f"Watching {KNOWLEDGE_PATH} for changes...")
    print(f"Sync interval: {interval_seconds}s")
    print("Press Ctrl+C to stop\n")

    last_sync = 0

    try:
        while True:
            # Simple polling approach
            current_time = time.time()

            # Check for recent modifications
            newest_mtime = 0
            for f in KNOWLEDGE_PATH.glob("**/*.md"):
                mtime = f.stat().st_mtime
                if mtime > newest_mtime:
                    newest_mtime = mtime

            # Sync if files changed since last sync
            if newest_mtime > last_sync:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Changes detected, syncing...")
                quick_sync()
                last_sync = current_time

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nStopped watching.")


# --- CLI ---

if __name__ == "__main__":
    import json

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "full":
            stats = run_full_index(include_vectors=True)
            print(f"\nStatus: {stats['status']}")

        elif cmd == "quick":
            stats = quick_sync()
            print(f"\nStatus: {stats['status']}")

        elif cmd == "watch":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            watch_and_sync(interval)

        elif cmd == "stats":
            from db.database import EntityRepository, JobRepository
            from rag.embeddings import EmbeddingStore

            print("\n=== Database Stats ===")
            for etype in ["project", "person", "client", "task", "decision"]:
                entities = EntityRepository.get_by_type(etype)
                print(f"  {etype}s: {len(entities)}")

            print("\n=== Job Stats ===")
            job_stats = JobRepository.get_stats()
            print(f"  Total jobs: {job_stats['total']}")
            for intent, count in job_stats.get('by_intent', {}).items():
                print(f"    {intent}: {count}")

            if CHROMADB_AVAILABLE:
                print("\n=== Vector Stats ===")
                store = EmbeddingStore()
                v_stats = store.get_stats()
                for collection, count in v_stats.items():
                    if collection != "path":
                        print(f"  {collection}: {count}")

        else:
            print(f"Unknown command: {cmd}")
            print("\nUsage:")
            print("  python indexer.py full    - Full index (SQLite + vectors)")
            print("  python indexer.py quick   - Quick sync (SQLite only)")
            print("  python indexer.py watch   - Watch and sync on changes")
            print("  python indexer.py stats   - Show index statistics")
    else:
        # Default: run full index
        run_full_index(include_vectors=True)
