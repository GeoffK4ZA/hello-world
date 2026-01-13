#!/usr/bin/env python3
"""
Geoff OS - CLI Tools

Unified command-line interface for database operations.

Usage:
    python -m src.cli <command> [args]

    or via the geoff command if installed:
    geoff <command> [args]
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import (
    init_database, EntityRepository, JobRepository,
    LearningRepository, PreferenceRepository, DB_PATH
)
from src.db.sync import sync_knowledge_base, sync_file_to_db, KNOWLEDGE_PATH
from src.jobs.tracker import JobTracker, format_job_summary

try:
    from src.rag.embeddings import EmbeddingStore, index_knowledge_base, CHROMADB_AVAILABLE
    from src.rag.retriever import Retriever, build_context_prompt
except ImportError:
    CHROMADB_AVAILABLE = False


def cmd_init(args):
    """Initialize database and optionally run full index."""
    print("Initializing Geoff OS database...")
    init_database()
    print(f"Database created at: {DB_PATH}")

    if args.full:
        from src.indexer import run_full_index
        run_full_index(include_vectors=args.vectors)


def cmd_sync(args):
    """Sync knowledge base to database."""
    if args.file:
        file_path = Path(args.file)
        entity = sync_file_to_db(file_path)
        if entity:
            print(f"Synced: {entity.id} ({entity.type})")
        else:
            print(f"Could not sync: {args.file}")
    else:
        print("Syncing knowledge base...")
        stats = sync_knowledge_base()
        print(f"Done: {stats['synced']} synced, {stats['skipped']} skipped, {stats['errors']} errors")


def cmd_search(args):
    """Search the knowledge base."""
    query = " ".join(args.query)

    if args.semantic and CHROMADB_AVAILABLE:
        # Vector search
        store = EmbeddingStore()
        results = store.search("knowledge", query, n_results=args.limit)
        print(f"\nSemantic search for: {query}\n")
        for doc in results:
            print(f"[{doc['id']}] (score: {1 - doc.get('distance', 0.5):.2f})")
            content = doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content']
            print(content)
            print()
    else:
        # FTS search
        entities = EntityRepository.search(query)
        print(f"\nFull-text search for: {query}\n")
        for entity in entities[:args.limit]:
            print(f"[{entity.type}] {entity.name}")
            if entity.content:
                content = entity.content[:200] + "..." if len(entity.content) > 200 else entity.content
                print(f"  {content}")
            print()


def cmd_retrieve(args):
    """Retrieve context for a query (RAG)."""
    query = " ".join(args.query)

    retriever = Retriever(use_vectors=CHROMADB_AVAILABLE)

    if args.intent:
        contexts = retriever.retrieve_for_intent(args.intent, query)
    else:
        contexts = retriever.retrieve(query, max_results=args.limit)

    if args.format == "prompt":
        print(build_context_prompt(contexts))
    else:
        print(f"\nRetrieved {len(contexts)} context items:\n")
        for ctx in contexts:
            print(f"[{ctx.source}] {ctx.id} (relevance: {ctx.relevance:.2f})")
            content = ctx.content[:300] + "..." if len(ctx.content) > 300 else ctx.content
            print(content)
            print()


def cmd_jobs(args):
    """Show job history and statistics."""
    tracker = JobTracker()

    if args.stats:
        stats = tracker.get_stats()
        print(json.dumps(stats, indent=2))
    else:
        jobs = tracker.get_recent_jobs(args.limit)
        print(format_job_summary(jobs))


def cmd_entities(args):
    """List entities by type."""
    entity_type = args.type

    if entity_type:
        entities = EntityRepository.get_by_type(entity_type)
    else:
        # Show counts by type
        types = ["project", "person", "client", "task", "decision", "preference", "pattern"]
        print("\nEntity counts:\n")
        for etype in types:
            entities = EntityRepository.get_by_type(etype)
            print(f"  {etype}s: {len(entities)}")
        return

    print(f"\n{entity_type.upper()}S ({len(entities)}):\n")
    for entity in entities:
        status = f" [{entity.status}]" if entity.status else ""
        print(f"  - {entity.name}{status}")


def cmd_stats(args):
    """Show overall statistics."""
    print("\n=== Geoff OS Statistics ===\n")

    # Database
    print("Database:")
    print(f"  Path: {DB_PATH}")
    if DB_PATH.exists():
        size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        print(f"  Size: {size_mb:.2f} MB")

    # Entities
    print("\nEntities:")
    types = ["project", "person", "client", "task", "decision"]
    for etype in types:
        entities = EntityRepository.get_by_type(etype)
        print(f"  {etype}s: {len(entities)}")

    # Jobs
    print("\nJobs:")
    job_stats = JobRepository.get_stats()
    print(f"  Total: {job_stats['total']}")
    for status, count in job_stats.get('by_status', {}).items():
        print(f"    {status}: {count}")

    # Vectors
    if CHROMADB_AVAILABLE:
        print("\nVector Store:")
        try:
            store = EmbeddingStore()
            v_stats = store.get_stats()
            for collection, count in v_stats.items():
                if collection != "path":
                    print(f"  {collection}: {count}")
        except Exception as e:
            print(f"  Error: {e}")

    # Knowledge files
    print("\nKnowledge Base:")
    print(f"  Path: {KNOWLEDGE_PATH}")
    md_files = list(KNOWLEDGE_PATH.glob("**/*.md"))
    print(f"  Files: {len(md_files)}")


def main():
    parser = argparse.ArgumentParser(
        prog="geoff",
        description="Geoff OS - Database CLI Tools"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    p_init = subparsers.add_parser("init", help="Initialize database")
    p_init.add_argument("--full", action="store_true", help="Run full index after init")
    p_init.add_argument("--vectors", action="store_true", help="Include vector embeddings")
    p_init.set_defaults(func=cmd_init)

    # sync
    p_sync = subparsers.add_parser("sync", help="Sync knowledge to database")
    p_sync.add_argument("--file", "-f", help="Sync single file")
    p_sync.set_defaults(func=cmd_sync)

    # search
    p_search = subparsers.add_parser("search", help="Search knowledge base")
    p_search.add_argument("query", nargs="+", help="Search query")
    p_search.add_argument("--semantic", "-s", action="store_true", help="Use semantic search")
    p_search.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    p_search.set_defaults(func=cmd_search)

    # retrieve
    p_retrieve = subparsers.add_parser("retrieve", help="Retrieve context (RAG)")
    p_retrieve.add_argument("query", nargs="+", help="Query")
    p_retrieve.add_argument("--intent", "-i", help="Intent type (brief, prep, task, status, draft)")
    p_retrieve.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    p_retrieve.add_argument("--format", "-f", choices=["list", "prompt"], default="list")
    p_retrieve.set_defaults(func=cmd_retrieve)

    # jobs
    p_jobs = subparsers.add_parser("jobs", help="Show job history")
    p_jobs.add_argument("--stats", action="store_true", help="Show statistics")
    p_jobs.add_argument("--limit", "-n", type=int, default=20, help="Max jobs")
    p_jobs.set_defaults(func=cmd_jobs)

    # entities
    p_entities = subparsers.add_parser("entities", help="List entities")
    p_entities.add_argument("--type", "-t", help="Entity type filter")
    p_entities.set_defaults(func=cmd_entities)

    # stats
    p_stats = subparsers.add_parser("stats", help="Show statistics")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
