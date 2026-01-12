"""
Digital Geoff Knowledge Graph

A graph-based knowledge store for:
- Projects and their relationships
- People and their roles/preferences
- Decisions and their context
- Documents and their connections

Integrates with Cognee for graph-based knowledge extraction
and Neo4j/Memgraph for graph storage.
"""

from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class EntityType(Enum):
    """Types of entities in the knowledge graph."""
    PERSON = "person"
    PROJECT = "project"
    TASK = "task"
    DOCUMENT = "document"
    MEETING = "meeting"
    DECISION = "decision"
    ORGANIZATION = "organization"
    TOPIC = "topic"
    SKILL = "skill"


class RelationType(Enum):
    """Types of relationships between entities."""
    # Person relationships
    WORKS_ON = "works_on"
    MANAGES = "manages"
    REPORTS_TO = "reports_to"
    COLLABORATES_WITH = "collaborates_with"
    KNOWS = "knows"

    # Project relationships
    DEPENDS_ON = "depends_on"
    BLOCKED_BY = "blocked_by"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    DELIVERS = "delivers"

    # Document relationships
    REFERENCES = "references"
    AUTHORED_BY = "authored_by"
    ABOUT = "about"

    # Decision relationships
    DECIDED_BY = "decided_by"
    AFFECTS = "affects"
    SUPERSEDES = "supersedes"

    # Temporal relationships
    PRECEDED_BY = "preceded_by"
    FOLLOWED_BY = "followed_by"
    SCHEDULED_FOR = "scheduled_for"


@dataclass
class Entity:
    """A node in the knowledge graph."""
    id: str
    type: EntityType
    name: str
    properties: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class Relationship:
    """An edge in the knowledge graph."""
    id: str
    type: RelationType
    from_entity_id: str
    to_entity_id: str
    properties: dict = field(default_factory=dict)
    strength: float = 1.0  # Relationship strength/weight
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "from": self.from_entity_id,
            "to": self.to_entity_id,
            "properties": self.properties,
            "strength": self.strength
        }


class GraphStore(ABC):
    """Abstract base for graph storage backends."""

    @abstractmethod
    async def add_entity(self, entity: Entity) -> str:
        pass

    @abstractmethod
    async def add_relationship(self, relationship: Relationship) -> str:
        pass

    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        pass

    @abstractmethod
    async def get_relationships(
        self,
        entity_id: str,
        direction: str = "both"
    ) -> list[Relationship]:
        pass

    @abstractmethod
    async def query(self, cypher: str) -> list[dict]:
        """Execute a graph query (Cypher-like)."""
        pass

    @abstractmethod
    async def search_entities(
        self,
        query: str,
        entity_type: Optional[EntityType] = None
    ) -> list[Entity]:
        pass


class InMemoryGraphStore(GraphStore):
    """In-memory graph store for development/testing."""

    def __init__(self):
        self.entities: dict[str, Entity] = {}
        self.relationships: dict[str, Relationship] = {}

    async def add_entity(self, entity: Entity) -> str:
        self.entities[entity.id] = entity
        return entity.id

    async def add_relationship(self, relationship: Relationship) -> str:
        self.relationships[relationship.id] = relationship
        return relationship.id

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        return self.entities.get(entity_id)

    async def get_relationships(
        self,
        entity_id: str,
        direction: str = "both"
    ) -> list[Relationship]:
        results = []
        for rel in self.relationships.values():
            if direction in ("both", "outgoing") and rel.from_entity_id == entity_id:
                results.append(rel)
            elif direction in ("both", "incoming") and rel.to_entity_id == entity_id:
                results.append(rel)
        return results

    async def query(self, cypher: str) -> list[dict]:
        # Simplified query support
        return []

    async def search_entities(
        self,
        query: str,
        entity_type: Optional[EntityType] = None
    ) -> list[Entity]:
        results = []
        query_lower = query.lower()
        for entity in self.entities.values():
            if entity_type and entity.type != entity_type:
                continue
            if query_lower in entity.name.lower():
                results.append(entity)
            elif any(query_lower in str(v).lower() for v in entity.properties.values()):
                results.append(entity)
        return results


class Neo4jGraphStore(GraphStore):
    """Production graph store using Neo4j."""

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        # Production: from neo4j import GraphDatabase
        # self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._fallback = InMemoryGraphStore()

    async def add_entity(self, entity: Entity) -> str:
        # Production Cypher:
        # CREATE (e:{entity.type.value} {id: $id, name: $name, ...})
        return await self._fallback.add_entity(entity)

    async def add_relationship(self, relationship: Relationship) -> str:
        # Production Cypher:
        # MATCH (a), (b) WHERE a.id = $from AND b.id = $to
        # CREATE (a)-[r:{relationship.type.value}]->(b)
        return await self._fallback.add_relationship(relationship)

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        return await self._fallback.get_entity(entity_id)

    async def get_relationships(
        self,
        entity_id: str,
        direction: str = "both"
    ) -> list[Relationship]:
        return await self._fallback.get_relationships(entity_id, direction)

    async def query(self, cypher: str) -> list[dict]:
        # Production: Execute actual Cypher query
        return await self._fallback.query(cypher)

    async def search_entities(
        self,
        query: str,
        entity_type: Optional[EntityType] = None
    ) -> list[Entity]:
        return await self._fallback.search_entities(query, entity_type)


class KnowledgeGraph:
    """
    High-level knowledge graph interface for Digital Geoff.

    Provides:
    - Entity and relationship management
    - Graph traversal and querying
    - Knowledge extraction from text
    - Context building for the agent
    """

    def __init__(self, store: GraphStore):
        self.store = store

    async def add_person(
        self,
        id: str,
        name: str,
        role: Optional[str] = None,
        organization: Optional[str] = None,
        communication_preferences: Optional[dict] = None,
        **properties
    ) -> Entity:
        """Add a person to the knowledge graph."""
        entity = Entity(
            id=id,
            type=EntityType.PERSON,
            name=name,
            properties={
                "role": role,
                "organization": organization,
                "communication_preferences": communication_preferences or {},
                **properties
            }
        )
        await self.store.add_entity(entity)
        return entity

    async def add_project(
        self,
        id: str,
        name: str,
        status: str = "active",
        deadline: Optional[str] = None,
        stakeholders: Optional[list[str]] = None,
        **properties
    ) -> Entity:
        """Add a project to the knowledge graph."""
        entity = Entity(
            id=id,
            type=EntityType.PROJECT,
            name=name,
            properties={
                "status": status,
                "deadline": deadline,
                "stakeholders": stakeholders or [],
                **properties
            }
        )
        await self.store.add_entity(entity)
        return entity

    async def add_decision(
        self,
        id: str,
        title: str,
        context: str,
        outcome: str,
        date: str,
        decided_by: list[str],
        affects: list[str],
        **properties
    ) -> Entity:
        """Record a decision in the knowledge graph."""
        entity = Entity(
            id=id,
            type=EntityType.DECISION,
            name=title,
            properties={
                "context": context,
                "outcome": outcome,
                "date": date,
                "decided_by": decided_by,
                "affects": affects,
                **properties
            }
        )
        await self.store.add_entity(entity)

        # Create relationships
        for person_id in decided_by:
            await self.link(entity.id, person_id, RelationType.DECIDED_BY)
        for affected_id in affects:
            await self.link(entity.id, affected_id, RelationType.AFFECTS)

        return entity

    async def link(
        self,
        from_id: str,
        to_id: str,
        relation_type: RelationType,
        properties: Optional[dict] = None,
        strength: float = 1.0
    ) -> Relationship:
        """Create a relationship between two entities."""
        rel_id = f"{from_id}-{relation_type.value}-{to_id}"
        relationship = Relationship(
            id=rel_id,
            type=relation_type,
            from_entity_id=from_id,
            to_entity_id=to_id,
            properties=properties or {},
            strength=strength
        )
        await self.store.add_relationship(relationship)
        return relationship

    async def query_relevant(self, context: dict) -> dict:
        """
        Query the graph for entities relevant to a given context.

        Returns entities and relationships that might be useful
        for the agent's current task.
        """
        results = {
            "entities": [],
            "relationships": []
        }

        # Extract potential entity references from context
        search_terms = self._extract_search_terms(context)

        for term in search_terms:
            # Search for matching entities
            entities = await self.store.search_entities(term)
            for entity in entities:
                results["entities"].append(entity.to_dict())

                # Get relationships for each found entity
                relationships = await self.store.get_relationships(entity.id)
                for rel in relationships:
                    results["relationships"].append(rel.to_dict())

        return results

    async def get_project_context(self, project_id: str) -> dict:
        """Get full context for a project including stakeholders, tasks, decisions."""
        project = await self.store.get_entity(project_id)
        if not project:
            return {}

        context = {
            "project": project.to_dict(),
            "stakeholders": [],
            "tasks": [],
            "decisions": [],
            "blockers": [],
            "related_projects": []
        }

        relationships = await self.store.get_relationships(project_id, "both")
        for rel in relationships:
            other_id = rel.to_entity_id if rel.from_entity_id == project_id else rel.from_entity_id
            other = await self.store.get_entity(other_id)

            if not other:
                continue

            if other.type == EntityType.PERSON:
                context["stakeholders"].append({
                    **other.to_dict(),
                    "relationship": rel.type.value
                })
            elif other.type == EntityType.TASK:
                context["tasks"].append(other.to_dict())
            elif other.type == EntityType.DECISION:
                context["decisions"].append(other.to_dict())
            elif other.type == EntityType.PROJECT:
                context["related_projects"].append({
                    **other.to_dict(),
                    "relationship": rel.type.value
                })

            if rel.type == RelationType.BLOCKED_BY:
                context["blockers"].append(other.to_dict())

        return context

    async def get_person_context(self, person_id: str) -> dict:
        """Get context about a person including their projects, communication history."""
        person = await self.store.get_entity(person_id)
        if not person:
            return {}

        context = {
            "person": person.to_dict(),
            "projects": [],
            "recent_interactions": [],
            "decisions_involved": [],
            "communication_preferences": person.properties.get("communication_preferences", {})
        }

        relationships = await self.store.get_relationships(person_id, "both")
        for rel in relationships:
            other_id = rel.to_entity_id if rel.from_entity_id == person_id else rel.from_entity_id
            other = await self.store.get_entity(other_id)

            if not other:
                continue

            if other.type == EntityType.PROJECT and rel.type == RelationType.WORKS_ON:
                context["projects"].append(other.to_dict())
            elif other.type == EntityType.DECISION:
                context["decisions_involved"].append(other.to_dict())

        return context

    def _extract_search_terms(self, context: dict) -> list[str]:
        """Extract potential entity names from a context dict."""
        terms = []

        if isinstance(context, dict):
            for key, value in context.items():
                if isinstance(value, str) and len(value) > 2:
                    # Split on common delimiters and add words
                    words = value.replace(",", " ").replace(".", " ").split()
                    for word in words:
                        if len(word) > 3 and word[0].isupper():
                            terms.append(word)
                elif isinstance(value, dict):
                    terms.extend(self._extract_search_terms(value))
        elif isinstance(context, str):
            words = context.replace(",", " ").replace(".", " ").split()
            for word in words:
                if len(word) > 3 and word[0].isupper():
                    terms.append(word)

        return list(set(terms))


# --- Knowledge Extraction ---

KNOWLEDGE_EXTRACTION_PROMPT = """Analyze this text and extract knowledge graph entities and relationships.

Text:
{text}

Extract:
1. ENTITIES (people, projects, organizations, decisions, documents)
2. RELATIONSHIPS between them

Output as JSON:
{{
  "entities": [
    {{
      "id": "unique_id",
      "type": "person|project|organization|decision|document|task",
      "name": "Entity Name",
      "properties": {{...}}
    }}
  ],
  "relationships": [
    {{
      "from": "entity_id",
      "to": "entity_id",
      "type": "works_on|manages|depends_on|blocked_by|related_to|...",
      "properties": {{}}
    }}
  ]
}}

Focus on:
- Named individuals and their roles
- Projects and their status/relationships
- Key decisions and who made them
- Dependencies and blockers
- Organizational relationships
"""
