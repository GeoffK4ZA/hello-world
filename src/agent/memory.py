"""
Digital Geoff Memory Layer

Implements a multi-tier memory system:
- Episodic: Past conversations, actions taken, outcomes
- Semantic: Facts about projects, people, preferences
- Procedural: How things are done, workflows, patterns

Integrates with:
- Mem0 for production-ready memory management
- Cognee for knowledge graph extraction
- Vector stores (Qdrant/Chroma) for semantic search
"""

import json
from datetime import datetime
from typing import Any, Literal, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import hashlib


MemoryType = Literal["episodic", "semantic", "procedural", "working"]


@dataclass
class MemoryRecord:
    """A single memory entry."""
    id: str
    content: str
    memory_type: MemoryType
    embedding: Optional[list[float]] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    importance: float = 0.5  # 0-1, for memory consolidation
    related_ids: list[str] = field(default_factory=list)


class MemoryStore(ABC):
    """Abstract base for memory storage backends."""

    @abstractmethod
    async def store(self, record: MemoryRecord) -> str:
        """Store a memory record, return ID."""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10
    ) -> list[MemoryRecord]:
        """Retrieve memories by semantic similarity."""
        pass

    @abstractmethod
    async def get_by_id(self, memory_id: str) -> Optional[MemoryRecord]:
        """Get a specific memory by ID."""
        pass

    @abstractmethod
    async def update(self, memory_id: str, updates: dict) -> bool:
        """Update a memory record."""
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory record."""
        pass


class Mem0MemoryStore(MemoryStore):
    """
    Production memory store using Mem0.

    Mem0 provides:
    - Automatic memory extraction from conversations
    - Graph-based memory relationships
    - Efficient retrieval with 91% lower latency
    - 90% token cost savings vs full context
    """

    def __init__(self, api_key: str, user_id: str):
        # In production: from mem0 import Memory
        self.api_key = api_key
        self.user_id = user_id
        self._memories: dict[str, MemoryRecord] = {}  # Local fallback

    async def store(self, record: MemoryRecord) -> str:
        """Store memory in Mem0."""
        # Production code:
        # self.client.add(
        #     messages=[{"role": "user", "content": record.content}],
        #     user_id=self.user_id,
        #     metadata=record.metadata
        # )

        self._memories[record.id] = record
        return record.id

    async def retrieve(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10
    ) -> list[MemoryRecord]:
        """Retrieve from Mem0 with semantic search."""
        # Production code:
        # results = self.client.search(query, user_id=self.user_id, limit=limit)
        # return [self._to_record(r) for r in results]

        # Local fallback: simple keyword matching
        results = []
        for record in self._memories.values():
            if memory_type and record.memory_type != memory_type:
                continue
            if query.lower() in record.content.lower():
                results.append(record)
        return results[:limit]

    async def get_by_id(self, memory_id: str) -> Optional[MemoryRecord]:
        return self._memories.get(memory_id)

    async def update(self, memory_id: str, updates: dict) -> bool:
        if memory_id in self._memories:
            record = self._memories[memory_id]
            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            return True
        return False

    async def delete(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False


class VectorMemoryStore(MemoryStore):
    """
    Vector-based memory store using Qdrant/Chroma.

    For semantic search over memories with embeddings.
    """

    def __init__(self, collection_name: str = "digital_geoff_memory"):
        self.collection_name = collection_name
        self._memories: dict[str, MemoryRecord] = {}
        # Production: Initialize Qdrant/Chroma client

    async def store(self, record: MemoryRecord) -> str:
        """Store with embedding."""
        # Production:
        # embedding = await self._get_embedding(record.content)
        # self.client.upsert(
        #     collection_name=self.collection_name,
        #     points=[{
        #         "id": record.id,
        #         "vector": embedding,
        #         "payload": record.to_dict()
        #     }]
        # )
        self._memories[record.id] = record
        return record.id

    async def retrieve(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10
    ) -> list[MemoryRecord]:
        """Semantic search with embeddings."""
        # Production:
        # query_embedding = await self._get_embedding(query)
        # results = self.client.search(
        #     collection_name=self.collection_name,
        #     query_vector=query_embedding,
        #     limit=limit,
        #     query_filter={"memory_type": memory_type} if memory_type else None
        # )

        results = list(self._memories.values())
        if memory_type:
            results = [r for r in results if r.memory_type == memory_type]
        return results[:limit]

    async def get_by_id(self, memory_id: str) -> Optional[MemoryRecord]:
        return self._memories.get(memory_id)

    async def update(self, memory_id: str, updates: dict) -> bool:
        if memory_id in self._memories:
            for key, value in updates.items():
                if hasattr(self._memories[memory_id], key):
                    setattr(self._memories[memory_id], key, value)
            return True
        return False

    async def delete(self, memory_id: str) -> bool:
        return self._memories.pop(memory_id, None) is not None


class MemoryManager:
    """
    High-level memory management for Digital Geoff.

    Coordinates across memory types and handles:
    - Memory extraction from conversations
    - Consolidation and importance scoring
    - Cross-type retrieval
    - Memory decay and cleanup
    """

    def __init__(
        self,
        episodic_store: MemoryStore,
        semantic_store: MemoryStore,
        procedural_store: MemoryStore,
        working_memory_size: int = 50
    ):
        self.stores = {
            "episodic": episodic_store,
            "semantic": semantic_store,
            "procedural": procedural_store
        }
        self.working_memory: list[MemoryRecord] = []
        self.working_memory_size = working_memory_size

    async def store(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[dict] = None,
        importance: float = 0.5
    ) -> str:
        """Store a new memory."""
        record = MemoryRecord(
            id=self._generate_id(content),
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
            importance=importance
        )

        # Store in appropriate backend
        if memory_type == "working":
            self.working_memory.append(record)
            if len(self.working_memory) > self.working_memory_size:
                # Consolidate oldest working memories
                await self._consolidate_working_memory()
            return record.id
        else:
            store = self.stores.get(memory_type)
            if store:
                return await store.store(record)
            raise ValueError(f"Unknown memory type: {memory_type}")

    async def retrieve(
        self,
        query: str,
        memory_types: Optional[list[MemoryType]] = None,
        limit: int = 10
    ) -> list[dict]:
        """
        Retrieve relevant memories across types.

        Returns unified list sorted by relevance.
        """
        types_to_search = memory_types or ["episodic", "semantic", "procedural"]
        all_results = []

        # Search working memory first (always relevant)
        for record in self.working_memory:
            if query.lower() in record.content.lower():
                all_results.append(self._record_to_dict(record))

        # Search each memory type
        for memory_type in types_to_search:
            store = self.stores.get(memory_type)
            if store:
                results = await store.retrieve(query, memory_type, limit=limit)
                for record in results:
                    all_results.append(self._record_to_dict(record))

        # Sort by relevance (in production: by embedding similarity score)
        # Deduplicate and limit
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result["id"] not in seen_ids:
                seen_ids.add(result["id"])
                unique_results.append(result)

        return unique_results[:limit]

    async def extract_and_store(
        self,
        conversation: list[dict],
        context: Optional[dict] = None
    ):
        """
        Extract memories from a conversation.

        Uses LLM to identify:
        - Facts to remember (semantic)
        - Events that happened (episodic)
        - Patterns/preferences learned (procedural)
        """
        # This would use Claude to extract structured memories
        # For now, store the conversation as episodic memory

        content = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in conversation
        ])

        await self.store(
            content=content,
            memory_type="episodic",
            metadata={"context": context or {}, "extracted": False}
        )

    async def get_context_window(self, max_tokens: int = 4000) -> str:
        """
        Build a context window from relevant memories.

        Prioritizes:
        1. Working memory (current session)
        2. Recent episodic (what happened recently)
        3. Relevant semantic (facts needed now)
        4. Applicable procedural (how to do things)
        """
        context_parts = []

        # Working memory
        if self.working_memory:
            context_parts.append("## Current Session Context")
            for record in self.working_memory[-10:]:  # Last 10 items
                context_parts.append(f"- {record.content}")

        # Recent episodic
        episodic = await self.stores["episodic"].retrieve("", limit=5)
        if episodic:
            context_parts.append("\n## Recent History")
            for record in episodic:
                context_parts.append(f"- [{record.created_at.strftime('%Y-%m-%d')}] {record.content[:200]}")

        return "\n".join(context_parts)

    async def _consolidate_working_memory(self):
        """Move old working memories to long-term storage."""
        if len(self.working_memory) <= self.working_memory_size:
            return

        # Move oldest memories to episodic
        to_consolidate = self.working_memory[:-self.working_memory_size]
        self.working_memory = self.working_memory[-self.working_memory_size:]

        for record in to_consolidate:
            record.memory_type = "episodic"
            await self.stores["episodic"].store(record)

    def _generate_id(self, content: str) -> str:
        """Generate a unique ID for a memory."""
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{content}{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _record_to_dict(self, record: MemoryRecord) -> dict:
        """Convert a memory record to a dictionary."""
        return {
            "id": record.id,
            "content": record.content,
            "type": record.memory_type,
            "created_at": record.created_at.isoformat(),
            "importance": record.importance,
            "metadata": record.metadata
        }


# --- Memory Extraction Prompts ---

MEMORY_EXTRACTION_PROMPT = """Analyze this conversation and extract memories to store.

Conversation:
{conversation}

Extract the following types of memories:

1. SEMANTIC (Facts):
- Names, roles, relationships
- Project details, deadlines, requirements
- Preferences, constraints, decisions made

2. EPISODIC (Events):
- What happened in this conversation
- Actions taken, outcomes achieved
- Problems encountered, solutions found

3. PROCEDURAL (Patterns):
- How the user likes things done
- Communication preferences
- Workflow patterns observed

Output as JSON:
{{
  "semantic": [
    {{"content": "...", "importance": 0.0-1.0}}
  ],
  "episodic": [
    {{"content": "...", "importance": 0.0-1.0}}
  ],
  "procedural": [
    {{"content": "...", "importance": 0.0-1.0}}
  ]
}}
"""
