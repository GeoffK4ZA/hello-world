"""
Geoff OS - Vector Embeddings with ChromaDB

Semantic search layer using ChromaDB for:
- Knowledge base vectorization
- Similarity search
- Context retrieval for RAG
"""

import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("ChromaDB not installed. Run: pip install chromadb")

# Paths
DATA_PATH = Path(__file__).parent.parent.parent / "data"
CHROMA_PATH = DATA_PATH / "chroma"
KNOWLEDGE_PATH = Path(__file__).parent.parent.parent / "knowledge"


class EmbeddingStore:
    """ChromaDB-based vector store for semantic search."""

    def __init__(self):
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("ChromaDB not installed")

        CHROMA_PATH.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )

        # Collections for different content types
        self.knowledge = self.client.get_or_create_collection(
            name="knowledge",
            metadata={"description": "Knowledge base documents"}
        )

        self.artefacts = self.client.get_or_create_collection(
            name="artefacts",
            metadata={"description": "Generated artefacts"}
        )

        self.interactions = self.client.get_or_create_collection(
            name="interactions",
            metadata={"description": "Past interactions and context"}
        )

    def add_document(
        self,
        collection_name: str,
        doc_id: str,
        content: str,
        metadata: Optional[Dict] = None
    ):
        """Add or update a document in the vector store."""
        collection = self._get_collection(collection_name)

        # Chunk large documents
        chunks = self._chunk_text(content)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}:chunk:{i}" if len(chunks) > 1 else doc_id

            chunk_metadata = {
                "doc_id": doc_id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "indexed_at": datetime.now().isoformat(),
                **(metadata or {})
            }

            # Upsert to handle updates
            collection.upsert(
                ids=[chunk_id],
                documents=[chunk],
                metadatas=[chunk_metadata]
            )

    def search(
        self,
        collection_name: str,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """Semantic search across a collection."""
        collection = self._get_collection(collection_name)

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata
        )

        # Format results
        formatted = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted.append({
                    "id": results['ids'][0][i] if results['ids'] else None,
                    "content": doc,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else None,
                    "distance": results['distances'][0][i] if results['distances'] else None
                })

        return formatted

    def search_all(
        self,
        query: str,
        n_results: int = 5
    ) -> Dict[str, List[Dict]]:
        """Search across all collections."""
        results = {}

        for name in ["knowledge", "artefacts", "interactions"]:
            try:
                results[name] = self.search(name, query, n_results)
            except Exception as e:
                results[name] = []
                print(f"Error searching {name}: {e}")

        return results

    def delete_document(self, collection_name: str, doc_id: str):
        """Delete a document and its chunks."""
        collection = self._get_collection(collection_name)

        # Get all chunk IDs for this document
        results = collection.get(
            where={"doc_id": doc_id}
        )

        if results['ids']:
            collection.delete(ids=results['ids'])

    def get_stats(self) -> Dict:
        """Get statistics about the vector store."""
        return {
            "knowledge": self.knowledge.count(),
            "artefacts": self.artefacts.count(),
            "interactions": self.interactions.count(),
            "path": str(CHROMA_PATH)
        }

    def _get_collection(self, name: str):
        """Get collection by name."""
        collections = {
            "knowledge": self.knowledge,
            "artefacts": self.artefacts,
            "interactions": self.interactions
        }
        if name not in collections:
            raise ValueError(f"Unknown collection: {name}")
        return collections[name]

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end near chunk boundary
                for sep in ['. ', '.\n', '\n\n', '\n']:
                    break_point = text.rfind(sep, start + chunk_size // 2, end)
                    if break_point != -1:
                        end = break_point + len(sep)
                        break

            chunks.append(text[start:end].strip())
            start = end - overlap

        return [c for c in chunks if c]  # Remove empty chunks


def index_knowledge_base(store: Optional[EmbeddingStore] = None) -> Dict:
    """Index all knowledge base files into vector store."""
    if store is None:
        store = EmbeddingStore()

    stats = {"indexed": 0, "skipped": 0, "errors": 0}

    for file_path in KNOWLEDGE_PATH.glob("**/*.md"):
        # Skip templates and READMEs
        if file_path.name.startswith('_') or file_path.name.lower() == 'readme.md':
            stats["skipped"] += 1
            continue

        try:
            content = file_path.read_text(encoding='utf-8')

            # Generate doc ID from path
            relative_path = file_path.relative_to(KNOWLEDGE_PATH)
            doc_id = str(relative_path).replace('/', ':').replace('.md', '')

            # Determine type from path
            doc_type = relative_path.parts[0] if relative_path.parts else "unknown"

            store.add_document(
                collection_name="knowledge",
                doc_id=doc_id,
                content=content,
                metadata={
                    "type": doc_type,
                    "file_path": str(relative_path),
                    "file_name": file_path.name
                }
            )
            stats["indexed"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"Error indexing {file_path}: {e}")

    return stats


# --- CLI ---

if __name__ == "__main__":
    import sys
    import json

    if not CHROMADB_AVAILABLE:
        print("ChromaDB not installed. Run: pip install chromadb")
        sys.exit(1)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "index":
            print("Indexing knowledge base...")
            store = EmbeddingStore()
            stats = index_knowledge_base(store)
            print(f"Done: {stats['indexed']} indexed, {stats['skipped']} skipped, {stats['errors']} errors")

        elif cmd == "search" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            store = EmbeddingStore()
            results = store.search_all(query, n_results=5)

            print(f"\nSearch results for: {query}\n")
            for collection, docs in results.items():
                if docs:
                    print(f"=== {collection.upper()} ===")
                    for doc in docs:
                        print(f"\n[{doc['id']}]")
                        print(doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'])
                    print()

        elif cmd == "stats":
            store = EmbeddingStore()
            stats = store.get_stats()
            print(json.dumps(stats, indent=2))

        else:
            print(f"Unknown command: {cmd}")
            print("Usage:")
            print("  python embeddings.py index           - Index knowledge base")
            print("  python embeddings.py search <query>  - Search vectors")
            print("  python embeddings.py stats           - Show statistics")
    else:
        print("Geoff OS - Vector Embeddings")
        print("\nCommands:")
        print("  index           - Index knowledge base")
        print("  search <query>  - Search vectors")
        print("  stats           - Show statistics")
