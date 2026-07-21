"""
Knowledge Base Service for GradeMIND.
Provides unified service layer for RAG context and curriculum lookups.
"""

import logging
from typing import List, Optional
from AI.knowledge_base.models import (
    Subject, Chapter, Topic, Question, ReferenceAnswer, Rubric, RubricCriterion
)
from AI.knowledge_base.curriculum_store import CurriculumStore
from AI.knowledge_base.question_store import QuestionStore
from AI.knowledge_base.answer_store import AnswerStore
from AI.knowledge_base.rubric_store import RubricStore

logger = logging.getLogger("GradeMIND.KnowledgeBaseService")


class KnowledgeBaseService:
    """
    Unified entrypoint for curriculum knowledge layers.
    """

    def __init__(self, seed: bool = True):
        self.curriculum_store = CurriculumStore()
        self.question_store = QuestionStore()
        self.answer_store = AnswerStore()
        self.rubric_store = RubricStore()

        if seed:
            self.seed_sample_curriculum()

    def get_subject(self, subject_id: str) -> Optional[Subject]:
        return self.curriculum_store.get_subject(subject_id)

    def get_chapter(self, chapter_id: str) -> Optional[Chapter]:
        return self.curriculum_store.get_chapter(chapter_id)

    def get_topic(self, topic_id: str) -> Optional[Topic]:
        return self.curriculum_store.get_topic(topic_id)

    def get_question(self, question_id: str) -> Optional[Question]:
        return self.question_store.get_question(question_id)

    def get_reference_answer(self, question_id: str) -> Optional[ReferenceAnswer]:
        return self.answer_store.get_reference_answer_by_question(question_id)

    def get_rubric(self, question_id: str) -> Optional[Rubric]:
        return self.rubric_store.get_rubric_by_question(question_id)

    def search_similar_questions(self, query: str, limit: int = 5) -> List[Question]:
        """
        Future vector search / RAG retrieval mock integration.
        Currently performs simple text filter.
        """
        results = []
        for q in self.question_store.list_questions():
            if query.lower() in q.question_text.lower():
                results.append(q)
        return results[:limit]

    def seed_sample_curriculum(self) -> None:
        """
        Seeds default subject, chapter, topic, question, answer, and rubric.
        """
        logger.info("Seeding academic knowledge base curriculum...")

        # 1. Seed Subject
        subject = Subject(
            id="sub_science",
            name="Science",
            code="SCI-101",
            description="General Science Curriculum"
        )
        self.curriculum_store.add_subject(subject)

        # 2. Seed Chapter
        chapter = Chapter(
            id="chap_photosynthesis",
            subject_id=subject.id,
            name="Photosynthesis",
            description="Understanding energy conversion in plants."
        )
        self.curriculum_store.add_chapter(chapter)

        # 3. Seed Topic
        topic = Topic(
            id="top_plant_nutrition",
            chapter_id=chapter.id,
            name="Plant Nutrition",
            learning_objectives=[
                "Understand how plants synthesize food.",
                "Describe the role of light, chlorophyll, and water."
            ]
        )
        self.curriculum_store.add_topic(topic)

        # 4. Seed Question
        question = Question(
            id="q_photosynthesis",
            topic_id=topic.id,
            question_text="What is photosynthesis?",
            difficulty="easy",
            marks=5.0
        )
        self.question_store.add_question(question)

        # 5. Seed Reference Answer
        answer = ReferenceAnswer(
            id="ans_photosynthesis",
            question_id=question.id,
            answer_text="Photosynthesis is the process by which plants convert sunlight into chemical energy."
        )
        self.answer_store.add_reference_answer(answer)

        # 6. Seed Rubric
        rubric = Rubric(
            id="rub_photosynthesis",
            question_id=question.id,
            title="Photosynthesis Evaluation Rubric"
        )
        self.rubric_store.add_rubric(rubric)

        # 7. Seed Criteria
        c1 = RubricCriterion(
            id="crit_photosynthesis_def",
            rubric_id=rubric.id,
            description="Definition",
            allocated_marks=2.0
        )
        c2 = RubricCriterion(
            id="crit_photosynthesis_inputs",
            rubric_id=rubric.id,
            description="Inputs",
            allocated_marks=1.5
        )
        c3 = RubricCriterion(
            id="crit_photosynthesis_outputs",
            rubric_id=rubric.id,
            description="Outputs",
            allocated_marks=1.5
        )
        self.rubric_store.add_criterion(c1)
        self.rubric_store.add_criterion(c2)
        self.rubric_store.add_criterion(c3)

        # Re-link criteria list back to rubric model
        self.rubric_store.add_rubric(rubric)

        logger.info("Knowledge base seeding complete.")
