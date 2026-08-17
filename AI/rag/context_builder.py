"""
Context Builder for GradeMIND RAG.
Aggregates retrieved vector search hits into a structured evaluation payload.
"""

from typing import List, Dict, Any


class ContextBuilder:
    """
    Constructs structured curriculum contexts from raw search results.
    """

    def build_context(self, retrieved_documents: List[Dict[str, Any]], query: str = "") -> Dict[str, Any]:
        """
        Organizes retrieved document chunks by type into a unified context dictionary.
        Filter documents by query relevance if multiple subject domains exist in retrieval results.
        """
        context = {
            "subject": "",
            "chapter": "",
            "topic": "",
            "question": "",
            "reference_answer": "",
            "rubric": []
        }

        if not retrieved_documents:
            return context

        q_low = query.lower() if query else ""
        if "photo" in q_low or "plant" in q_low or "science" in q_low:
            matched = [d for d in retrieved_documents if any(w in d.get("content", "").lower() for w in ["photo", "science", "plant", "nutrition"])]
            if matched:
                retrieved_documents = matched
        elif any(w in q_low for w in ["array", "linked", "stack", "queue", "dsa"]):
            matched = [d for d in retrieved_documents if any(w in d.get("content", "").lower() for w in ["dsa", "structure", "array", "linked"])]
            if matched:
                retrieved_documents = matched

        seen_types = set()
        sorted_docs = sorted(retrieved_documents, key=lambda x: x.get("score", 0.0), reverse=True)

        for doc in sorted_docs:
            doc_type = doc.get("document_type", "").lower()
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            # 1. Subject Context
            if doc_type == "subject" and "subject" not in seen_types:
                context["subject"] = content
                seen_types.add("subject")

            # 2. Chapter Context
            elif doc_type == "chapter" and "chapter" not in seen_types:
                context["chapter"] = content
                seen_types.add("chapter")

            # 3. Topic Context
            elif doc_type == "topic" and "topic" not in seen_types:
                context["topic"] = content
                seen_types.add("topic")

            # 4. Question Context
            elif doc_type == "question" and "question" not in seen_types:
                context["question"] = content
                seen_types.add("question")

            # 5. Reference Answer Context
            elif doc_type == "referenceanswer" and "reference_answer" not in seen_types:
                context["reference_answer"] = content
                seen_types.add("reference_answer")

            # 6. Rubric Context
            elif doc_type == "rubric":
                # Rubrics can have a list of criteria stored in metadata
                criteria_list = metadata.get("criteria", [])
                rubric_title = content
                
                rubric_entry = {
                    "title": rubric_title,
                    "criteria": criteria_list
                }
                
                # Check to avoid duplicate rubrics
                if rubric_title not in [r["title"] for r in context["rubric"]]:
                    context["rubric"].append(rubric_entry)

        return context
