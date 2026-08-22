"""
Answer Store for GradeMIND.
Manages ReferenceAnswer records in memory.
"""

from typing import List, Dict, Optional
from AI.knowledge_base.models import ReferenceAnswer


class AnswerStore:
    """
    Repository for reference answers mapped to questions.
    """

    def __init__(self):
        self._answers: Dict[str, ReferenceAnswer] = {}

    def add_reference_answer(self, answer: ReferenceAnswer) -> ReferenceAnswer:
        self._answers[answer.id] = answer
        return answer

    def get_reference_answer(self, id: str) -> Optional[ReferenceAnswer]:
        return self._answers.get(id)

    def get_reference_answer_by_question(self, question_id: str) -> Optional[ReferenceAnswer]:
        for ans in self._answers.values():
            if ans.question_id == question_id:
                return ans
        return None

    def list_reference_answers(self) -> List[ReferenceAnswer]:
        return list(self._answers.values())

    def clear(self) -> None:
        self._answers.clear()
