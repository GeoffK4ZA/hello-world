"""
Geoff OS - Job Tracker

Database-backed job execution tracking for:
- Audit trail of all operations
- Context logging (what knowledge was used)
- Performance monitoring
- Error tracking
"""

import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from dataclasses import dataclass, asdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import Job, JobRepository, db_session, init_database


@dataclass
class JobContext:
    """Context used during job execution."""
    files_read: List[str]
    entities_queried: List[str]
    search_queries: List[str]
    artefacts_created: List[str]


class JobTracker:
    """
    Track job execution with full audit trail.

    Usage:
        tracker = JobTracker()
        with tracker.track("brief", source="telegram") as job:
            # Do work
            job.add_context_file("knowledge/tasks/active.md")
            job.set_output({"artefact": "/artefacts/briefs/2024-01-15.md"})
    """

    def __init__(self):
        init_database()

    @contextmanager
    def track(
        self,
        intent: str,
        source: str = "cli",
        inputs: Optional[Dict] = None
    ):
        """
        Context manager for tracking a job.

        Args:
            intent: Job type (brief, prep, task, draft, status, query)
            source: Where the job originated (cli, telegram, scheduler)
            inputs: Input parameters

        Yields:
            TrackedJob instance for adding context during execution
        """
        job = TrackedJob(
            id=f"job:{datetime.now().strftime('%Y%m%d%H%M%S')}:{uuid.uuid4().hex[:8]}",
            intent=intent,
            source=source,
            inputs=inputs
        )

        # Create job record
        JobRepository.create(Job(
            id=job.id,
            intent=job.intent,
            status="running",
            source=job.source,
            inputs=job.inputs
        ))

        start_time = time.time()

        try:
            yield job

            # Success
            duration_ms = int((time.time() - start_time) * 1000)
            JobRepository.update_status(
                job_id=job.id,
                status="completed",
                outputs=job.outputs,
                context_used=job.context.files_read + job.context.entities_queried,
                duration_ms=duration_ms
            )

        except Exception as e:
            # Failure
            duration_ms = int((time.time() - start_time) * 1000)
            JobRepository.update_status(
                job_id=job.id,
                status="failed",
                error=str(e),
                context_used=job.context.files_read,
                duration_ms=duration_ms
            )
            raise

    def get_recent_jobs(self, limit: int = 20) -> List[Job]:
        """Get recent job history."""
        return JobRepository.get_recent(limit)

    def get_stats(self) -> Dict:
        """Get job statistics."""
        return JobRepository.get_stats()

    def get_context_for_query(self, query: str) -> List[str]:
        """Get files commonly used for similar queries."""
        # Find similar past jobs and return their context
        with db_session() as conn:
            rows = conn.execute("""
                SELECT context_used FROM jobs
                WHERE intent = 'query' AND status = 'completed'
                AND inputs LIKE ?
                ORDER BY created_at DESC
                LIMIT 5
            """, (f'%{query[:20]}%',)).fetchall()

            context_files = []
            for row in rows:
                if row['context_used']:
                    import json
                    files = json.loads(row['context_used'])
                    context_files.extend(files)

            return list(set(context_files))


class TrackedJob:
    """A job being tracked with context accumulation."""

    def __init__(
        self,
        id: str,
        intent: str,
        source: str,
        inputs: Optional[Dict] = None
    ):
        self.id = id
        self.intent = intent
        self.source = source
        self.inputs = inputs
        self.outputs: Dict = {}
        self.context = JobContext(
            files_read=[],
            entities_queried=[],
            search_queries=[],
            artefacts_created=[]
        )

    def add_context_file(self, file_path: str):
        """Record a file that was read for context."""
        if file_path not in self.context.files_read:
            self.context.files_read.append(file_path)

    def add_entity_query(self, entity_id: str):
        """Record an entity that was queried."""
        if entity_id not in self.context.entities_queried:
            self.context.entities_queried.append(entity_id)

    def add_search_query(self, query: str):
        """Record a search query that was executed."""
        self.context.search_queries.append(query)

    def add_artefact(self, artefact_path: str):
        """Record an artefact that was created."""
        if artefact_path not in self.context.artefacts_created:
            self.context.artefacts_created.append(artefact_path)

    def set_output(self, outputs: Dict):
        """Set job outputs."""
        self.outputs = outputs

    def add_output(self, key: str, value: Any):
        """Add to job outputs."""
        self.outputs[key] = value


def format_job_summary(jobs: List[Job]) -> str:
    """Format job list as readable summary."""
    if not jobs:
        return "No jobs found."

    lines = ["## Recent Jobs\n"]
    lines.append("| Time | Intent | Status | Duration | Source |")
    lines.append("|------|--------|--------|----------|--------|")

    for job in jobs:
        time_str = job.created_at[:16] if job.created_at else "?"
        duration = f"{job.duration_ms}ms" if job.duration_ms else "-"
        status_icon = {"completed": "✓", "failed": "✗", "running": "⟳"}.get(job.status, "?")

        lines.append(f"| {time_str} | {job.intent} | {status_icon} {job.status} | {duration} | {job.source or '-'} |")

    return "\n".join(lines)


# --- CLI ---

if __name__ == "__main__":
    import sys
    import json

    tracker = JobTracker()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "list":
            jobs = tracker.get_recent_jobs(20)
            print(format_job_summary(jobs))

        elif cmd == "stats":
            stats = tracker.get_stats()
            print(json.dumps(stats, indent=2))

        elif cmd == "test":
            # Test job tracking
            print("Running test job...")
            with tracker.track("test", source="cli", inputs={"test": True}) as job:
                job.add_context_file("knowledge/test.md")
                job.set_output({"result": "success"})
                time.sleep(0.1)  # Simulate work
            print(f"Job completed: {job.id}")

        else:
            print(f"Unknown command: {cmd}")
            print("Usage:")
            print("  python tracker.py list    - List recent jobs")
            print("  python tracker.py stats   - Show job statistics")
            print("  python tracker.py test    - Run test job")
    else:
        print("Geoff OS - Job Tracker")
        print("\nCommands:")
        print("  list    - List recent jobs")
        print("  stats   - Show job statistics")
        print("  test    - Run test job")
