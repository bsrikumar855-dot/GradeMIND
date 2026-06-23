"""
Embedding service for GradeMIND.
Generates local embeddings using SentenceTransformers with fallback and caching.
"""

import logging
from typing import List, Union, Dict
import numpy as np

logger = logging.getLogger("GradeMIND.EmbeddingService")

class EmbeddingService:
    _model = None
    _model_name = None
    _cache: Dict[str, List[float]] = {}  # Global/Class-level cache for string -> embedding list

    def __init__(
        self, 
        model_name: str = "BAAI/bge-large-en-v1.5", 
        fallback_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.model_name = model_name
        self.fallback_model_name = fallback_model_name

    def _get_model(self):
        """
        Lazily loads the SentenceTransformer model (with fallback).
        """
        if EmbeddingService._model is not None:
            return EmbeddingService._model
        
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Initializing preferred embedding model: %s", self.model_name)
            EmbeddingService._model = SentenceTransformer(self.model_name)
            EmbeddingService._model_name = self.model_name
            return EmbeddingService._model
        except Exception as e:
            logger.warning(
                "Failed to load preferred model %s: %s. Attempting fallback: %s", 
                self.model_name, e, self.fallback_model_name
            )
            try:
                from sentence_transformers import SentenceTransformer
                EmbeddingService._model = SentenceTransformer(self.fallback_model_name)
                EmbeddingService._model_name = self.fallback_model_name
                logger.info("Successfully loaded fallback embedding model: %s", self.fallback_model_name)
                return EmbeddingService._model
            except Exception as e_fallback:
                logger.error(
                    "Failed to load fallback embedding model %s: %s", 
                    self.fallback_model_name, e_fallback
                )
                raise RuntimeError("Could not load any local embedding model.") from e_fallback

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text. Uses cache if available.
        """
        if not isinstance(text, str):
            text = str(text) if text is not None else ""
            
        clean_text = text.strip()
        if not clean_text:
            model = self._get_model()
            dim = model.get_sentence_embedding_dimension()
            return np.zeros(dim, dtype=np.float32)

        # Check cache
        if clean_text in EmbeddingService._cache:
            return np.array(EmbeddingService._cache[clean_text], dtype=np.float32)

        model = self._get_model()
        try:
            # Generate embedding
            emb = model.encode(clean_text, convert_to_numpy=True)
            # Store in cache
            EmbeddingService._cache[clean_text] = emb.tolist()
            return emb
        except Exception as e:
            logger.exception("Error generating embedding for text: %r", clean_text[:50])
            # Return zero vector on failure to prevent pipeline crashes
            dim = model.get_sentence_embedding_dimension()
            return np.zeros(dim, dtype=np.float32)

    def generate_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for a list of texts. Optimizes by retrieving cached
        embeddings and only encoding non-cached texts in a single batch.
        """
        if not texts:
            return []

        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        model = self._get_model()
        dim = model.get_sentence_embedding_dimension()

        for idx, text in enumerate(texts):
            if not isinstance(text, str):
                text = str(text) if text is not None else ""
            
            clean_text = text.strip()
            if not clean_text:
                results[idx] = np.zeros(dim, dtype=np.float32)
                continue

            if clean_text in EmbeddingService._cache:
                results[idx] = np.array(EmbeddingService._cache[clean_text], dtype=np.float32)
            else:
                uncached_indices.append(idx)
                uncached_texts.append(clean_text)

        # Encode uncached in a batch
        if uncached_texts:
            try:
                logger.info("Generating batch embeddings for %d uncached texts", len(uncached_texts))
                batch_embs = model.encode(uncached_texts, convert_to_numpy=True, batch_size=32)
                for index_in_batch, original_idx in enumerate(uncached_indices):
                    emb = batch_embs[index_in_batch]
                    clean_text = uncached_texts[index_in_batch]
                    EmbeddingService._cache[clean_text] = emb.tolist()
                    results[original_idx] = emb
            except Exception as e:
                logger.exception("Error in batch embedding generation")
                # Fallback individually to be safe
                for original_idx in uncached_indices:
                    results[original_idx] = self.generate_embedding(texts[original_idx])

        return results
