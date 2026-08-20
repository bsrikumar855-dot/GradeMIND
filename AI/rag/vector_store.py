"""
In-Memory Vector Store for GradeMIND.
Stores VectorRecords and performs local cosine similarity searches.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from pydantic import BaseModel, Field


class VectorRecord(BaseModel):
    """
    Structured vector database record.
    """
    document_id: str = Field(..., description="Unique ID of the academic document.")
    document_type: str = Field(..., description="Type: Subject, Chapter, Topic, Question, ReferenceAnswer, Rubric.")
    content: str = Field(..., description="Text content indexed for search.")
    embedding: List[float] = Field(..., description="Calculated vector embedding representation.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata tags (e.g. subject_id, chapter_id).")


class VectorStore:
    """
    Local memory-backed vector database.
    """

    def __init__(self):
        self._records: Dict[str, VectorRecord] = {}

    def add_document(
        self, 
        document_id: str, 
        document_type: str, 
        content: str, 
        embedding: List[float], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> VectorRecord:
        """
        Inserts a single document vector record.
        """
        record = VectorRecord(
            document_id=document_id,
            document_type=document_type,
            content=content,
            embedding=embedding,
            metadata=metadata or {}
        )
        self._records[document_id] = record
        return record

    def add_documents(self, documents: List[VectorRecord]) -> None:
        """
        Inserts multiple document vector records.
        """
        for doc in documents:
            self._records[doc.document_id] = doc

    def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[VectorRecord, float]]:
        """
        Computes cosine similarity between query_embedding and all stored vectors.
        Filters by metadata before computing similarity if filters are provided.
        Returns a list of Tuple[VectorRecord, score] sorted in descending order.
        """
        if not self._records or not query_embedding:
            return []

        q_vec = np.asarray(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0.0:
            return []

        results = []
        for record in self._records.values():
            if metadata_filters:
                match = True
                for k, v in metadata_filters.items():
                    if k == "document_type":
                        # special handling for document type to allow case-insensitive
                        if record.document_type.lower() != str(v).lower():
                            match = False
                            break
                    elif str(record.metadata.get(k, "")).lower() != str(v).lower():
                        match = False
                        break
                if not match:
                    continue
                    
            r_vec = np.asarray(record.embedding, dtype=np.float32)
            r_norm = np.linalg.norm(r_vec)
            if r_norm == 0.0:
                similarity = 0.0
            else:
                similarity = float(np.dot(q_vec, r_vec) / (q_norm * r_norm))
                # Clip to 0.0 -> 1.0 boundary
                similarity = float(np.clip(similarity, 0.0, 1.0))
            
            results.append((record, similarity))

        # Sort descending by similarity score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def delete(self, document_id: str) -> bool:
        """
        Deletes a vector record by document ID.
        """
        if document_id in self._records:
            del self._records[document_id]
            return True
        return False

    def count(self) -> int:
        """
        Returns the total number of indexed vectors.
        """
        return len(self._records)

    def clear(self) -> None:
        """
        Clears all stored records.
        """
        self._records.clear()
