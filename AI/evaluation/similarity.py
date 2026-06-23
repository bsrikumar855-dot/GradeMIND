"""
Similarity engine for GradeMIND.
Computes Cosine Similarity between embeddings.
"""

import logging
import numpy as np

logger = logging.getLogger("GradeMIND.SimilarityEngine")

class SimilarityEngine:
    """
    Computes cosine similarity between text embeddings.
    """

    def calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Calculates the cosine similarity between two vector embeddings.
        Outputs are clipped to the range [0.0, 1.0].
        """
        try:
            v1 = np.asarray(emb1, dtype=np.float32)
            v2 = np.asarray(emb2, dtype=np.float32)

            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)

            if norm1 == 0.0 or norm2 == 0.0:
                return 0.0

            cosine_sim = np.dot(v1, v2) / (norm1 * norm2)
            
            # Clip between 0.0 and 1.0 to handle minor floating-point inaccuracies
            # and map negative similarity to 0.0
            return float(np.clip(cosine_sim, 0.0, 1.0))
        except Exception as e:
            logger.exception("Error calculating similarity")
            return 0.0
