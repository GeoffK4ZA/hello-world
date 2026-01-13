"""
Geoff OS - RAG (Retrieval Augmented Generation)

Components:
- embeddings: ChromaDB vector store
- retriever: Multi-strategy context retrieval
"""

from .retriever import Retriever, RetrievedContext, build_context_prompt

__all__ = ['Retriever', 'RetrievedContext', 'build_context_prompt']
