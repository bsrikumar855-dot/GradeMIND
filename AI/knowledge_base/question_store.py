"""
Question Store for GradeMIND.
Manages Question records in memory.
"""

from typing import List, Dict, Optional
from AI.knowledge_base.models import Question


class QuestionStore:
    """
    Repository for academic questions.
    """

    def __init__(self):
        self._questions: Dict[str, Question] = {}

    def add_question(self, question: Question) -> Question:
        self._questions[question.id] = question
        return question

    def get_question(self, id: str) -> Optional[Question]:
        return self._questions.get(id)

    def list_questions(self) -> List[Question]:
        return list(self._questions.values())

    def get_questions_by_topic(self, topic_id: str) -> List[Question]:
        return [q for q in self._questions.values() if q.topic_id == topic_id]

    def clear(self) -> None:
        self._questions.clear()
