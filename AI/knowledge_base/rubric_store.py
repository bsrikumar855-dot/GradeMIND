"""
Rubric Store for GradeMIND.
Manages Rubric and RubricCriterion records in memory.
"""

from typing import List, Dict, Optional
from AI.knowledge_base.models import Rubric, RubricCriterion


class RubricStore:
    """
    Repository for rubrics and criteria associated with academic questions.
    """

    def __init__(self):
        self._rubrics: Dict[str, Rubric] = {}
        self._criteria: Dict[str, RubricCriterion] = {}

    def add_rubric(self, rubric: Rubric) -> Rubric:
        # Link criteria if they exist in store
        rubric.criteria = self.get_criteria_by_rubric(rubric.id)
        self._rubrics[rubric.id] = rubric
        return rubric

    def get_rubric(self, id: str) -> Optional[Rubric]:
        rubric = self._rubrics.get(id)
        if rubric:
            rubric.criteria = self.get_criteria_by_rubric(id)
        return rubric

    def get_rubric_by_question(self, question_id: str) -> Optional[Rubric]:
        for rub in self._rubrics.values():
            if rub.question_id == question_id:
                # Reload criteria to ensure full structure
                rub.criteria = self.get_criteria_by_rubric(rub.id)
                return rub
        return None

    def list_rubrics(self) -> List[Rubric]:
        for rub in self._rubrics.values():
            rub.criteria = self.get_criteria_by_rubric(rub.id)
        return list(self._rubrics.values())

    def add_criterion(self, criterion: RubricCriterion) -> RubricCriterion:
        self._criteria[criterion.id] = criterion
        # Update associated rubric if it exists
        if criterion.rubric_id in self._rubrics:
            rubric = self._rubrics[criterion.rubric_id]
            if criterion not in rubric.criteria:
                rubric.criteria = self.get_criteria_by_rubric(criterion.rubric_id)
        return criterion

    def get_criterion(self, id: str) -> Optional[RubricCriterion]:
        return self._criteria.get(id)

    def get_criteria_by_rubric(self, rubric_id: str) -> List[RubricCriterion]:
        return [c for c in self._criteria.values() if c.rubric_id == rubric_id]

    def clear(self) -> None:
        self._rubrics.clear()
        self._criteria.clear()
