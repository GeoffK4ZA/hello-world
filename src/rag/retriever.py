"""
Geoff OS - RAG Retriever

Context retrieval pipeline that combines:
- SQLite full-text search (exact matching)
- ChromaDB semantic search (similarity)
- Entity relationship traversal (graph)

Returns ranked, deduplicated context for any query.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from ..db.database import EntityRepository, RelationshipRepository, db_session
from .embeddings import EmbeddingStore, CHROMADB_AVAILABLE

KNOWLEDGE_PATH = Path(__file__).parent.parent.parent / "knowledge"


@dataclass
class RetrievedContext:
    """A piece of retrieved context."""
    id: str
    content: str
    source: str  # fts, vector, relationship, file
    relevance: float
    metadata: Optional[Dict] = None


class Retriever:
    """Multi-strategy context retriever."""

    def __init__(self, use_vectors: bool = True):
        self.use_vectors = use_vectors and CHROMADB_AVAILABLE
        self.vector_store = EmbeddingStore() if self.use_vectors else None

    def retrieve(
        self,
        query: str,
        max_results: int = 10,
        entity_types: Optional[List[str]] = None,
        include_relationships: bool = True
    ) -> List[RetrievedContext]:
        """
        Retrieve relevant context using multiple strategies.

        Args:
            query: Search query
            max_results: Maximum results to return
            entity_types: Filter by entity types (project, person, etc.)
            include_relationships: Include related entities

        Returns:
            Ranked list of context items
        """
        seen_ids: Set[str] = set()
        results: List[RetrievedContext] = []

        # 1. Full-text search in SQLite
        fts_results = self._search_fts(query, entity_types)
        for ctx in fts_results:
            if ctx.id not in seen_ids:
                results.append(ctx)
                seen_ids.add(ctx.id)

        # 2. Vector similarity search
        if self.use_vectors:
            vector_results = self._search_vectors(query)
            for ctx in vector_results:
                if ctx.id not in seen_ids:
                    results.append(ctx)
                    seen_ids.add(ctx.id)

        # 3. Expand with related entities
        if include_relationships:
            entity_ids = [r.id for r in results if r.source in ('fts', 'vector')]
            for entity_id in entity_ids[:5]:  # Limit expansion
                related = self._get_related(entity_id)
                for ctx in related:
                    if ctx.id not in seen_ids:
                        results.append(ctx)
                        seen_ids.add(ctx.id)

        # 4. Direct file matches for specific patterns
        file_results = self._search_files(query)
        for ctx in file_results:
            if ctx.id not in seen_ids:
                results.append(ctx)
                seen_ids.add(ctx.id)

        # Sort by relevance and limit
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:max_results]

    def retrieve_for_intent(
        self,
        intent: str,
        args: Optional[str] = None
    ) -> List[RetrievedContext]:
        """
        Retrieve context based on command intent.

        Args:
            intent: Command type (brief, prep, task, status, draft)
            args: Command arguments

        Returns:
            Context relevant to the intent
        """
        results = []

        if intent == "brief":
            # Get active tasks, today's priorities, recent decisions
            results.extend(self._search_fts("active", ["task"]))
            results.extend(self._search_fts("high priority", ["task", "project"]))
            results.extend(self._get_recent_files("tasks"))

        elif intent == "prep":
            # Get meeting attendees, project context
            if args:
                results.extend(self.retrieve(args, max_results=10))
                # Look for person profiles
                results.extend(self._search_fts(args, ["person"]))
                results.extend(self._search_fts(args, ["project"]))

        elif intent == "status":
            # Get project info, blockers, stakeholders
            if args:
                results.extend(self.retrieve(args, max_results=10, entity_types=["project"]))
                results.extend(self._search_fts(args, ["task"]))

        elif intent == "task":
            # Get related projects and context
            if args:
                results.extend(self.retrieve(args, max_results=5))

        elif intent == "draft":
            # Get communication preferences, templates
            results.extend(self._search_fts("communication", ["preference"]))
            results.extend(self._search_fts("email", ["template"]))
            if args:
                results.extend(self.retrieve(args, max_results=5))

        # Deduplicate
        seen = set()
        unique = []
        for ctx in results:
            if ctx.id not in seen:
                unique.append(ctx)
                seen.add(ctx.id)

        return unique[:15]

    def _search_fts(
        self,
        query: str,
        entity_types: Optional[List[str]] = None
    ) -> List[RetrievedContext]:
        """Full-text search in SQLite."""
        results = []

        try:
            if entity_types:
                for etype in entity_types:
                    entities = EntityRepository.search(query, etype)
                    for entity in entities:
                        results.append(RetrievedContext(
                            id=entity.id,
                            content=f"# {entity.name}\n\n{entity.content or ''}",
                            source="fts",
                            relevance=0.8,
                            metadata={"type": entity.type, "status": entity.status}
                        ))
            else:
                entities = EntityRepository.search(query)
                for entity in entities:
                    results.append(RetrievedContext(
                        id=entity.id,
                        content=f"# {entity.name}\n\n{entity.content or ''}",
                        source="fts",
                        relevance=0.8,
                        metadata={"type": entity.type, "status": entity.status}
                    ))
        except Exception as e:
            # FTS might not be initialized yet
            pass

        return results

    def _search_vectors(self, query: str) -> List[RetrievedContext]:
        """Semantic search in ChromaDB."""
        if not self.vector_store:
            return []

        results = []

        try:
            vector_results = self.vector_store.search("knowledge", query, n_results=5)

            for doc in vector_results:
                # Convert distance to relevance (lower distance = higher relevance)
                relevance = 1.0 - (doc.get('distance', 0.5) or 0.5)

                results.append(RetrievedContext(
                    id=doc.get('id', 'unknown'),
                    content=doc.get('content', ''),
                    source="vector",
                    relevance=relevance,
                    metadata=doc.get('metadata')
                ))
        except Exception as e:
            pass

        return results

    def _get_related(self, entity_id: str) -> List[RetrievedContext]:
        """Get related entities via relationship graph."""
        results = []

        try:
            relationships = RelationshipRepository.get_for_entity(entity_id)

            for rel in relationships[:5]:  # Limit related items
                related_entity = EntityRepository.get(rel['related_id'])
                if related_entity:
                    results.append(RetrievedContext(
                        id=related_entity.id,
                        content=f"# {related_entity.name}\n\n{related_entity.content or ''}",
                        source="relationship",
                        relevance=0.5,
                        metadata={
                            "type": related_entity.type,
                            "relationship": rel['relationship']
                        }
                    ))
        except Exception:
            pass

        return results

    def _search_files(self, query: str) -> List[RetrievedContext]:
        """Direct file search for specific patterns."""
        results = []

        # Extract potential entity references
        patterns = [
            (r'@(\w+)', 'person'),  # @name references
            (r'#(\w+)', 'project'),  # #project tags
        ]

        for pattern, entity_type in patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                file_path = KNOWLEDGE_PATH / f"{entity_type}s" / f"{match.lower()}.md"
                if file_path.exists():
                    content = file_path.read_text(encoding='utf-8')
                    results.append(RetrievedContext(
                        id=f"file:{file_path.stem}",
                        content=content,
                        source="file",
                        relevance=0.9,
                        metadata={"file_path": str(file_path)}
                    ))

        return results

    def _get_recent_files(
        self,
        directory: str,
        limit: int = 5
    ) -> List[RetrievedContext]:
        """Get recently modified files from a directory."""
        results = []

        dir_path = KNOWLEDGE_PATH / directory
        if not dir_path.exists():
            return results

        # Get files sorted by modification time
        files = sorted(
            dir_path.glob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        for file_path in files[:limit]:
            if file_path.name.startswith('_') or file_path.name.lower() == 'readme.md':
                continue

            content = file_path.read_text(encoding='utf-8')
            results.append(RetrievedContext(
                id=f"file:{directory}:{file_path.stem}",
                content=content,
                source="file",
                relevance=0.6,
                metadata={"file_path": str(file_path)}
            ))

        return results


def build_context_prompt(
    contexts: List[RetrievedContext],
    max_tokens: int = 4000
) -> str:
    """
    Build a context prompt from retrieved items.

    Args:
        contexts: List of retrieved context items
        max_tokens: Approximate max tokens (using char count / 4)

    Returns:
        Formatted context string for prompt injection
    """
    if not contexts:
        return ""

    lines = ["## Retrieved Context\n"]
    char_count = 0
    max_chars = max_tokens * 4  # Rough token to char ratio

    for ctx in contexts:
        # Format context item
        header = f"### [{ctx.metadata.get('type', 'unknown').upper()}] {ctx.id}"
        content = ctx.content[:1000] if len(ctx.content) > 1000 else ctx.content

        entry = f"{header}\n{content}\n\n"
        entry_chars = len(entry)

        if char_count + entry_chars > max_chars:
            break

        lines.append(entry)
        char_count += entry_chars

    lines.append(f"---\n*{len(contexts)} context items retrieved*\n")

    return "\n".join(lines)


# --- CLI ---

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])

        print(f"Retrieving context for: {query}\n")

        retriever = Retriever(use_vectors=CHROMADB_AVAILABLE)
        results = retriever.retrieve(query, max_results=5)

        if results:
            prompt = build_context_prompt(results)
            print(prompt)
        else:
            print("No context found.")
    else:
        print("Geoff OS - RAG Retriever")
        print("\nUsage: python retriever.py <query>")
        print("\nExample:")
        print("  python retriever.py project status")
        print("  python retriever.py meeting with client")
