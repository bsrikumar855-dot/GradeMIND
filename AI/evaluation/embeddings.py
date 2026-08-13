"""
Embedding service for GradeMIND.

Generates local embeddings using SentenceTransformers.

SCORING-PATH INVARIANT
----------------------
This module sits in the scoring path: its output feeds semantic value-point
matching, and a different vector produces a different mark. It therefore has
no fallbacks. Every failure mode raises.

Specifically, none of the following are permitted here:

  * loading a different model when the configured one fails to load
    (a substituted model silently changes every similarity score);
  * returning a zero vector when encoding fails
    (a zero vector has cosine similarity 0.0 against everything, which
    silently scores the answer as matching nothing);
  * degrading a batch encode into per-item encodes that then zero-fill.

All three existed in earlier revisions of this file. They are the reason the
same answer could receive different marks on different runs. If a model cannot
be loaded or a text cannot be encoded, the worker fails and the job retries or
dead-letters. It never guesses.

See docs/audit/BASELINE_AUDIT.md N5.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("GradeMIND.EmbeddingService")

# The embedding model is a scoring input. It is configuration, never a literal
# buried in code, and it is recorded on every evaluation record alongside the
# weights hash so a result can be reproduced.
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"


class EmbeddingModelUnavailable(RuntimeError):
    """The configured embedding model could not be loaded.

    Raised instead of substituting a different model. Callers must treat this
    as a job failure, not as a reason to score the answer.
    """


class EmbeddingFailed(RuntimeError):
    """A text could not be encoded.

    Raised instead of returning a zero vector.
    """


class EmbeddingService:
    """Loads one embedding model and encodes text with it.

    Models are cached per model name for the lifetime of the process. The cache
    is keyed by name so that two services configured with different models
    cannot silently share one — an earlier revision cached a single model on
    the class, so whichever instance loaded first decided the model for every
    other instance.
    """

    _models: Dict[str, object] = {}
    _fingerprints: Dict[str, str] = {}
    _load_lock = threading.Lock()

    # Encoding cache, keyed by (model_name, text) for the same reason.
    _cache: Dict[Tuple[str, str], List[float]] = {}

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = (
            model_name
            or os.environ.get("EMBEDDING_MODEL")
            or DEFAULT_EMBEDDING_MODEL
        )

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _get_model(self) -> Any:
        """Load the configured model, or raise.

        There is deliberately no fallback model. See the module docstring.
        """
        cached = EmbeddingService._models.get(self.model_name)
        if cached is not None:
            return cached

        with EmbeddingService._load_lock:
            # Re-check: another thread may have loaded it while we waited.
            cached = EmbeddingService._models.get(self.model_name)
            if cached is not None:
                return cached

            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingModelUnavailable(
                    "sentence-transformers is not installed; the semantic "
                    "scoring path cannot run. Install requirements/ai.txt."
                ) from exc

            logger.info("Loading embedding model: %s", self.model_name)
            try:
                model = SentenceTransformer(self.model_name)
            except Exception as exc:
                # No fallback. A substituted model is an unlogged scoring change.
                raise EmbeddingModelUnavailable(
                    f"Could not load embedding model {self.model_name!r}. "
                    "Refusing to substitute a different model, because that "
                    "would change every similarity score without record."
                ) from exc

            EmbeddingService._models[self.model_name] = model
            logger.info("Loaded embedding model: %s", self.model_name)
            return model

    def weights_sha256(self) -> str:
        """Stable fingerprint of the loaded weights.

        Recorded on the evaluation record together with ``model_name`` so a
        stored result can be reproduced, and so a silently swapped set of
        weights behind an unchanged model name is detectable.
        """
        cached = EmbeddingService._fingerprints.get(self.model_name)
        if cached is not None:
            return cached

        model = self._get_model()
        digest = hashlib.sha256()
        state = model.state_dict()
        for key in sorted(state):
            tensor = state[key].detach().cpu()
            # Cast to a single dtype so the digest does not depend on whether
            # the weights happened to load as float16/bfloat16/float32.
            digest.update(key.encode("utf-8"))
            digest.update(tensor.to(dtype=_float32()).numpy().tobytes())

        fingerprint = digest.hexdigest()
        EmbeddingService._fingerprints[self.model_name] = fingerprint
        return fingerprint

    def provenance(self) -> Dict[str, str]:
        """The pair that must land on every evaluation record."""
        return {
            "embedding_model_name": self.model_name,
            "embedding_weights_sha256": self.weights_sha256(),
        }

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def generate_embedding(self, text: str) -> np.ndarray:
        """Encode one text. Raises rather than returning a zero vector."""
        clean_text = _clean(text)
        model = self._get_model()

        if not clean_text:
            # Genuinely empty input is a real, representable case: the answer
            # is blank. The zero vector here is a statement about the input,
            # not a swallowed error.
            return np.zeros(model.get_sentence_embedding_dimension(), dtype=np.float32)

        cache_key = (self.model_name, clean_text)
        cached = EmbeddingService._cache.get(cache_key)
        if cached is not None:
            return np.array(cached, dtype=np.float32)

        try:
            emb = model.encode(clean_text, convert_to_numpy=True)
        except Exception as exc:
            raise EmbeddingFailed(
                f"Failed to encode text with {self.model_name!r} "
                f"({len(clean_text)} chars). Refusing to return a zero vector, "
                "which would score the answer as matching nothing."
            ) from exc

        vector = np.asarray(emb, dtype=np.float32)
        EmbeddingService._cache[cache_key] = vector.tolist()
        return vector

    def generate_batch_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Encode many texts. Raises rather than degrading to zero vectors."""
        if not texts:
            return []

        model = self._get_model()
        dim = model.get_sentence_embedding_dimension()

        results: List[Optional[np.ndarray]] = [None] * len(texts)
        uncached_indices: List[int] = []
        uncached_texts: List[str] = []

        for idx, text in enumerate(texts):
            clean_text = _clean(text)
            if not clean_text:
                results[idx] = np.zeros(dim, dtype=np.float32)
                continue

            cached = EmbeddingService._cache.get((self.model_name, clean_text))
            if cached is not None:
                results[idx] = np.array(cached, dtype=np.float32)
            else:
                uncached_indices.append(idx)
                uncached_texts.append(clean_text)

        if uncached_texts:
            logger.info(
                "Encoding %d uncached texts with %s",
                len(uncached_texts),
                self.model_name,
            )
            try:
                batch = model.encode(
                    uncached_texts, convert_to_numpy=True, batch_size=32
                )
            except Exception as exc:
                raise EmbeddingFailed(
                    f"Batch encode of {len(uncached_texts)} texts failed with "
                    f"{self.model_name!r}. Refusing to fall back to per-item "
                    "encoding that zero-fills on failure."
                ) from exc

            for position, original_idx in enumerate(uncached_indices):
                emb = batch[position]
                EmbeddingService._cache[
                    (self.model_name, uncached_texts[position])
                ] = emb.tolist()
                results[original_idx] = emb

        missing = [i for i, r in enumerate(results) if r is None]
        if missing:
            # Unreachable by construction; assert it rather than ship a None
            # into a numpy op and get an opaque error three frames away.
            raise EmbeddingFailed(
                f"Internal error: {len(missing)} texts produced no embedding "
                f"(indices {missing[:10]})."
            )

        return [r for r in results if r is not None]


def _clean(text: object) -> str:
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    return text.strip()


def _float32() -> Any:
    import torch

    return torch.float32
