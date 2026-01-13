"""
Geoff OS - Markdown <-> SQLite Sync

Bidirectional synchronization between markdown knowledge files and SQLite database.
- Parses markdown frontmatter and content
- Extracts entities and relationships
- Keeps both stores in sync
"""

import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .database import (
    Entity, Relationship, EntityRepository, RelationshipRepository,
    db_session, init_database
)

# Knowledge directory paths
KNOWLEDGE_PATH = Path(__file__).parent.parent.parent / "knowledge"
ARTEFACTS_PATH = Path(__file__).parent.parent.parent / "artefacts"


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter from markdown content."""
    frontmatter = {}
    body = content

    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if match:
        fm_text, body = match.groups()
        for line in fm_text.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip().strip('"\'')

    return frontmatter, body.strip()


def generate_id(type_: str, name: str) -> str:
    """Generate consistent ID from type and name."""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return f"{type_}:{slug}"


def extract_relationships(content: str, entity_id: str) -> List[Relationship]:
    """Extract relationships from markdown content."""
    relationships = []

    # Pattern: [[entity_type:entity_name]]
    link_pattern = r'\[\[(\w+):([^\]]+)\]\]'
    for match in re.finditer(link_pattern, content):
        ref_type, ref_name = match.groups()
        ref_id = generate_id(ref_type, ref_name)
        relationships.append(Relationship(
            from_entity_id=entity_id,
            to_entity_id=ref_id,
            relationship_type="references"
        ))

    # Pattern: @person_name (people references)
    person_pattern = r'@(\w+(?:\s+\w+)?)'
    for match in re.finditer(person_pattern, content):
        person_name = match.group(1)
        person_id = generate_id("person", person_name)
        relationships.append(Relationship(
            from_entity_id=entity_id,
            to_entity_id=person_id,
            relationship_type="mentions"
        ))

    # Pattern: #project_name (project tags)
    project_pattern = r'#(\w+[-\w]*)'
    for match in re.finditer(project_pattern, content):
        project_name = match.group(1)
        # Avoid hashtags that are markdown headers
        if not content[match.start()-1:match.start()].strip().endswith('\n'):
            continue
        project_id = generate_id("project", project_name)
        relationships.append(Relationship(
            from_entity_id=entity_id,
            to_entity_id=project_id,
            relationship_type="tagged"
        ))

    return relationships


def determine_entity_type(file_path: Path) -> Optional[str]:
    """Determine entity type from file path."""
    parts = file_path.parts

    # Map directory to entity type
    type_map = {
        "projects": "project",
        "people": "person",
        "clients": "client",
        "tasks": "task",
        "decisions": "decision",
        "preferences": "preference",
        "patterns": "pattern",
        "learnings": "learning",
        "templates": "template"
    }

    for part in parts:
        if part in type_map:
            return type_map[part]

    return None


def sync_file_to_db(file_path: Path) -> Optional[Entity]:
    """Sync a single markdown file to the database."""
    if not file_path.exists() or not file_path.suffix == '.md':
        return None

    entity_type = determine_entity_type(file_path)
    if not entity_type:
        return None

    content = file_path.read_text(encoding='utf-8')
    frontmatter, body = parse_frontmatter(content)

    # Extract name from frontmatter or filename
    name = frontmatter.get('title') or frontmatter.get('name') or file_path.stem.replace('-', ' ').replace('_', ' ').title()

    entity_id = generate_id(entity_type, name)

    # Build entity
    entity = Entity(
        id=entity_id,
        type=entity_type,
        name=name,
        status=frontmatter.get('status'),
        priority=frontmatter.get('priority'),
        content=body,
        metadata=frontmatter if frontmatter else None,
        file_path=str(file_path.relative_to(file_path.parent.parent.parent))
    )

    # Check if entity exists
    existing = EntityRepository.get(entity_id)
    if existing:
        EntityRepository.update(entity)
    else:
        EntityRepository.create(entity)

    # Extract and save relationships
    relationships = extract_relationships(body, entity_id)
    for rel in relationships:
        try:
            RelationshipRepository.create(rel)
        except Exception:
            pass  # Related entity might not exist yet

    return entity


def sync_db_to_file(entity: Entity) -> Optional[Path]:
    """Sync a database entity back to markdown file."""
    if not entity.file_path:
        # Generate file path from entity type and name
        type_dir_map = {
            "project": "projects",
            "person": "people",
            "client": "clients",
            "task": "tasks",
            "decision": "decisions",
            "preference": "preferences",
            "pattern": "patterns"
        }

        dir_name = type_dir_map.get(entity.type, entity.type + "s")
        slug = re.sub(r'[^a-z0-9]+', '-', entity.name.lower()).strip('-')
        file_path = KNOWLEDGE_PATH / dir_name / f"{slug}.md"
    else:
        file_path = Path(entity.file_path)
        if not file_path.is_absolute():
            file_path = KNOWLEDGE_PATH.parent / file_path

    # Build frontmatter
    frontmatter_lines = ["---"]
    frontmatter_lines.append(f"title: {entity.name}")
    if entity.status:
        frontmatter_lines.append(f"status: {entity.status}")
    if entity.priority:
        frontmatter_lines.append(f"priority: {entity.priority}")
    if entity.metadata:
        for key, value in entity.metadata.items():
            if key not in ('title', 'name', 'status', 'priority'):
                frontmatter_lines.append(f"{key}: {value}")
    frontmatter_lines.append(f"updated: {datetime.now().isoformat()}")
    frontmatter_lines.append("---")

    # Build content
    content = "\n".join(frontmatter_lines) + "\n\n" + (entity.content or "")

    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    file_path.write_text(content, encoding='utf-8')

    return file_path


def sync_directory(directory: Path, recursive: bool = True) -> Dict:
    """Sync all markdown files in a directory to database."""
    stats = {"synced": 0, "skipped": 0, "errors": 0}

    pattern = "**/*.md" if recursive else "*.md"

    for file_path in directory.glob(pattern):
        # Skip templates and README files
        if file_path.name.startswith('_') or file_path.name.lower() == 'readme.md':
            stats["skipped"] += 1
            continue

        try:
            entity = sync_file_to_db(file_path)
            if entity:
                stats["synced"] += 1
            else:
                stats["skipped"] += 1
        except Exception as e:
            stats["errors"] += 1
            print(f"Error syncing {file_path}: {e}")

    return stats


def sync_knowledge_base() -> Dict:
    """Full sync of knowledge base to database."""
    # Initialize database if needed
    init_database()

    total_stats = {"synced": 0, "skipped": 0, "errors": 0}

    # Sync knowledge directory
    if KNOWLEDGE_PATH.exists():
        stats = sync_directory(KNOWLEDGE_PATH)
        for key in total_stats:
            total_stats[key] += stats[key]

    return total_stats


def get_content_hash(content: str) -> str:
    """Generate hash of content for change detection."""
    return hashlib.md5(content.encode()).hexdigest()


def detect_changes(file_path: Path) -> Optional[str]:
    """Check if file has changed since last sync."""
    if not file_path.exists():
        return None

    entity_type = determine_entity_type(file_path)
    if not entity_type:
        return None

    content = file_path.read_text(encoding='utf-8')
    frontmatter, body = parse_frontmatter(content)
    name = frontmatter.get('title') or frontmatter.get('name') or file_path.stem.replace('-', ' ').title()
    entity_id = generate_id(entity_type, name)

    existing = EntityRepository.get(entity_id)
    if not existing:
        return "new"

    # Compare content
    if existing.content != body:
        return "modified"

    return None


# --- CLI ---

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "sync":
            print("Syncing knowledge base to database...")
            stats = sync_knowledge_base()
            print(f"Done: {stats['synced']} synced, {stats['skipped']} skipped, {stats['errors']} errors")

        elif cmd == "file" and len(sys.argv) > 2:
            file_path = Path(sys.argv[2])
            entity = sync_file_to_db(file_path)
            if entity:
                print(f"Synced: {entity.id} ({entity.type})")
            else:
                print("Could not sync file")

        elif cmd == "export" and len(sys.argv) > 2:
            entity_id = sys.argv[2]
            entity = EntityRepository.get(entity_id)
            if entity:
                file_path = sync_db_to_file(entity)
                print(f"Exported to: {file_path}")
            else:
                print(f"Entity not found: {entity_id}")

        else:
            print(f"Unknown command: {cmd}")
            print("Usage:")
            print("  python sync.py sync              - Sync all knowledge to DB")
            print("  python sync.py file <path>       - Sync single file")
            print("  python sync.py export <entity_id> - Export entity to markdown")
    else:
        print("Geoff OS - Markdown <-> SQLite Sync")
        print("\nCommands:")
        print("  sync              - Sync all knowledge to DB")
        print("  file <path>       - Sync single file")
        print("  export <entity_id> - Export entity to markdown")
