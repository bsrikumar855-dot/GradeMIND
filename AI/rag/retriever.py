"""
Retriever layer for GradeMIND RAG.
Orchestrates EmbeddingService queries against the VectorStore.
"""

from typing import List, Dict, Any
from AI.rag.embedding_service import EmbeddingService
from AI.rag.vector_store import VectorStore


class Retriever:
    """
    Handles semantic querying over indexed vectors.
    """

    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Generates embedding for the query, searches the vector store,
        and returns ranked records with cosine similarity scores.
        """
        if not query or not query.strip():
            return []

        # 1. Generate query embedding
        query_emb = self.embedding_service.embed_text(query)

        # 2. Query vector store
        search_results = self.vector_store.search(query_emb, top_k=top_k)

        # 3. Format ranked results
        ranked_results = []
        for record, score in search_results:
            ranked_results.append({
                "document_id": record.document_id,
                "document_type": record.document_type,
                "content": record.content,
                "score": round(score, 4),
                "metadata": record.metadata
            })
            
        return ranked_results
