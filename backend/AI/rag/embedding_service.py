"""
RAG Embedding Service wrapper for GradeMIND.
Wraps the existing evaluation EmbeddingService for consistency.
"""

import os
from typing import List, Optional
from AI.evaluation.embeddings import EmbeddingService as EvalEmbeddingService


class EmbeddingService:
    """
    Service to generate embeddings for text chunks using local inference.
    """

    def __init__(self, model_name: Optional[str] = None):
        target_model = (
            model_name
            or os.environ.get("EMBEDDING_MODEL")
            or "sentence-transformers/all-MiniLM-L6-v2"
        )
        # Delegate to existing robust evaluation embedding service
        self._service = EvalEmbeddingService(model_name=target_model)


    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.
        """
        emb = self._service.generate_embedding(text)
        return emb.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for a list of texts.
        """
        embs = self._service.generate_batch_embeddings(texts)
        return [emb.tolist() for emb in embs]
