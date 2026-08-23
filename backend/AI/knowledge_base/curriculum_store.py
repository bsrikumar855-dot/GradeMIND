"""
Curriculum Store for GradeMIND.
Manages Subject, Chapter, and Topic repository tables in memory.
"""

from typing import List, Dict, Optional
from AI.knowledge_base.models import Subject, Chapter, Topic


class CurriculumStore:
    """
    Repository for academic subjects, chapters, and topics.
    """

    def __init__(self):
        self._subjects: Dict[str, Subject] = {}
        self._chapters: Dict[str, Chapter] = {}
        self._topics: Dict[str, Topic] = {}

    def add_subject(self, subject: Subject) -> Subject:
        self._subjects[subject.id] = subject
        return subject

    def get_subject(self, id: str) -> Optional[Subject]:
        return self._subjects.get(id)

    def list_subjects(self) -> List[Subject]:
        return list(self._subjects.values())

    def add_chapter(self, chapter: Chapter) -> Chapter:
        self._chapters[chapter.id] = chapter
        return chapter

    def get_chapter(self, id: str) -> Optional[Chapter]:
        return self._chapters.get(id)

    def list_chapters(self) -> List[Chapter]:
        return list(self._chapters.values())

    def get_chapters_by_subject(self, subject_id: str) -> List[Chapter]:
        return [c for c in self._chapters.values() if c.subject_id == subject_id]

    def add_topic(self, topic: Topic) -> Topic:
        self._topics[topic.id] = topic
        return topic

    def get_topic(self, id: str) -> Optional[Topic]:
        return self._topics.get(id)

    def list_topics(self) -> List[Topic]:
        return list(self._topics.values())

    def get_topics_by_chapter(self, chapter_id: str) -> List[Topic]:
        return [t for t in self._topics.values() if t.chapter_id == chapter_id]

    def clear(self) -> None:
        self._subjects.clear()
        self._chapters.clear()
        self._topics.clear()
