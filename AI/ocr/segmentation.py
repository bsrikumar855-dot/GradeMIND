"""Question Segmentation — mapping page transcriptions to question regions.

Extracts question numbers, groups transcribed lines by question, handles page-spanning
questions, and rejoins mid-word line splits.

ROUTING RULE
------------
Every QuestionRegion whose status is NOT SegmentationStatus.OK (including SPANS_PAGES,
MISSING_QUESTION_NUMBER, AMBIGUOUS_MAPPING, OUT_OF_ORDER, UNMAPPED_REGION) must route
to MANDATORY_HUMAN.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

from AI.ocr.providers.base import Line, Page

logger = logging.getLogger("GradeMIND.Segmentation")

SEGMENTATION_VERSION = "segmentation/1.0.0"


class SegmentationStatus(str, Enum):
    OK = "OK"
    SPANS_PAGES = "SPANS_PAGES"
    AMBIGUOUS_CONTINUATION = "AMBIGUOUS_CONTINUATION"
    MISSING_QUESTION_NUMBER = "MISSING_QUESTION_NUMBER"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    UNMAPPED_REGION = "UNMAPPED_REGION"


@dataclass(frozen=True)
class QuestionRegion:
    """The transcribed text and lines belonging to one question."""

    question_number: str
    page_numbers: Tuple[int, ...]
    text: str
    confidence: Optional[float]
    status: SegmentationStatus
    lines: Tuple[Line, ...] = ()

    def can_be_auto(self) -> bool:
        """OK and SPANS_PAGES (when cleanly stitched) allow AUTO consideration downstream.
        AMBIGUOUS_CONTINUATION, MISSING_QUESTION_NUMBER, AMBIGUOUS_MAPPING,
        OUT_OF_ORDER, and UNMAPPED_REGION route to MANDATORY_HUMAN.
        """
        return self.status in (SegmentationStatus.OK, SegmentationStatus.SPANS_PAGES)


def is_section_header(text: str) -> bool:
    """Detect section header boundaries like 'Part B', 'Section A', 'PART - B'.

    A section header is a structural boundary that terminates the active question
    from the previous page/section.
    """
    raw = text.strip()
    if not raw:
        return False

    # Pure section header without question number (e.g. "Part B", "Section A", "PART - B")
    return bool(re.match(r'^(?:Part|Section|Group|Block)\s*[-:\s]*[A-Z0-9]+\s*$', raw, re.IGNORECASE))


def parse_question_header(text: str) -> Optional[str]:
    """Detect a question number header at the start of a line.

    Matches patterns like:
      - "13.", "14.", "15."
      - "1. c)", "Q1.", "Q13", "Q.15"
      - "Part B 13."
    Returns the normalized question number string (e.g. "13", "14", "1"), or None.
    """
    raw = text.strip()
    if not raw:
        return None

    # Section header check (handled separately)
    if is_section_header(raw):
        return None

    # Pattern 1: Bare question number on line (e.g., "13.", "14.", "15.", "13")
    m_bare = re.match(r'^(?:Part\s+[A-Z]\s*)?(?:Q\.?\s*)?(\d{1,3})\s*[\.\)]?\s*$', raw, re.IGNORECASE)
    if m_bare:
        return m_bare.group(1)

    # Pattern 2: Question number at start of line followed by text (e.g. "13. Standard autoencoders", "1. c) contractive")
    m_start = re.match(r'^(?:Part\s+[A-Z]\s*)?(?:Q\.?\s*)?(\d{1,3})\s*[\.\)]\s*(.*)$', raw, re.IGNORECASE)
    if m_start:
        q_num = m_start.group(1)
        return q_num

    return None


def rejoin_line_texts(lines_text: Sequence[str]) -> str:
    """Stitch lines of text together, correctly rejoining mid-word splits.

    Rules:
      - If line A ends with a hyphen ('-'), strip hyphen and join directly to line B ('import-' + 'ant' -> 'important').
      - If line A ends with a word/letter (no punctuation/space) and line B starts with a lowercase continuation
        span (e.g. 'import' + 'ant'), rejoin without space -> 'important'.
      - Otherwise, join with a single space.
    """
    if not lines_text:
        return ""

    result = []
    for i, line in enumerate(lines_text):
        clean = line.strip()
        if not clean:
            continue

        if not result:
            result.append(clean)
            continue

        prev = result[-1]

        # Case 1: Hyphenated split at line end ("import-" + "ant" -> "important")
        if prev.endswith("-"):
            result[-1] = prev[:-1] + clean
            continue

        # Case 2: Mid-word split across lines without hyphen ("import" + "ant" -> "important")
        # Trigger: prev ends with letter, clean starts with lowercase letters, and prev_token is an unclosed fragment (not a complete common word)
        _COMMON_WORDS = {
            "a", "about", "after", "all", "also", "an", "and", "any", "are", "as", "at", "be",
            "been", "but", "by", "can", "come", "could", "day", "do", "even", "first", "for",
            "from", "get", "give", "go", "good", "had", "has", "have", "he", "her", "him", "his",
            "how", "i", "if", "in", "into", "is", "it", "its", "just", "know", "like", "look",
            "make", "many", "me", "more", "most", "my", "no", "not", "now", "of", "on", "one",
            "only", "or", "other", "our", "out", "over", "people", "said", "say", "see", "she",
            "so", "some", "take", "than", "that", "the", "their", "them", "then", "there", "these",
            "they", "think", "this", "time", "to", "two", "up", "us", "use", "want", "was",
            "way", "we", "well", "were", "what", "when", "which", "who", "will", "with", "would",
            "year", "you", "your",
        }

        m_prev_word = re.search(r'([A-Za-z]+)$', prev)
        m_curr_word = re.match(r'^([a-z]+)\b', clean)

        if m_prev_word and m_curr_word:
            prev_token = m_prev_word.group(1)
            curr_token = m_curr_word.group(1)
            if prev_token.lower() not in _COMMON_WORDS:
                if len(curr_token) <= 3 or prev_token.lower() in ("import", "auto", "micro", "multi", "sub"):
                    prefix = prev[:-len(prev_token)]
                    joined_word = prev_token + curr_token
                    rest_curr = clean[len(curr_token):]
                    result[-1] = prefix + joined_word + rest_curr
                    continue

        # Default: Join with space
        result.append(clean)

    return " ".join(result)


def segment_script(
    pages: Sequence[Page],
    expected_questions: Optional[Sequence[str]] = None,
) -> List[QuestionRegion]:
    """Segment a sequence of pages into QuestionRegions.

    Stitches continuation text across pages, flags SPANS_PAGES, checks ordering,
    and returns QuestionRegions.
    """
    if not pages:
        return []

    # Temporary accumulation structure
    accumulated_q: List[dict] = []
    current: Optional[dict] = None

    for page in pages:
        for line in page.lines:
            # Check for section header boundary (e.g. "Part B", "Section A")
            if is_section_header(line.text):
                if current is not None:
                    accumulated_q.append(current)
                    current = None
                continue

            header_q = parse_question_header(line.text)

            if header_q is not None:
                # Start new question region
                if current is not None:
                    accumulated_q.append(current)

                current = {
                    "question_number": header_q,
                    "pages": [page.page_number],
                    "lines": [line],
                }
            else:
                # Continuation text for current question or unmapped leading text
                if current is None:
                    # Unmapped leading text before first question header
                    current = {
                        "question_number": "UNMAPPED",
                        "pages": [page.page_number],
                        "lines": [line],
                    }
                else:
                    if page.page_number not in current["pages"]:
                        current["pages"].append(page.page_number)
                    current["lines"].append(line)

    if current is not None:
        accumulated_q.append(current)

    # Convert accumulated questions into QuestionRegion objects and assign status
    regions: List[QuestionRegion] = []
    seen_q_numbers = []

    for q_data in accumulated_q:
        q_num = q_data["question_number"]
        page_nums = tuple(q_data["pages"])
        q_lines = tuple(q_data["lines"])

        # Rejoin text
        line_texts = [l.text for l in q_lines]
        full_text = rejoin_line_texts(line_texts)

        # Calculate lowest confidence among lines
        confs = [l.confidence for l in q_lines if l.confidence is not None]
        confidence = min(confs) if confs else None

        # Determine status
        if q_num == "UNMAPPED":
            status = SegmentationStatus.UNMAPPED_REGION
        elif q_num in seen_q_numbers:
            status = SegmentationStatus.AMBIGUOUS_MAPPING
        elif len(page_nums) > 1:
            status = SegmentationStatus.SPANS_PAGES
        else:
            status = SegmentationStatus.OK

        seen_q_numbers.append(q_num)

        regions.append(
            QuestionRegion(
                question_number=q_num,
                page_numbers=page_nums,
                text=full_text,
                confidence=confidence,
                status=status,
                lines=q_lines,
            )
        )

    # Check for OUT_OF_ORDER
    numeric_qs = []
    for r in regions:
        if r.question_number.isdigit():
            numeric_qs.append(int(r.question_number))

    if numeric_qs and numeric_qs != sorted(numeric_qs):
        # Mark all or affected regions as OUT_OF_ORDER
        new_regions = []
        for r in regions:
            if r.status == SegmentationStatus.OK:
                new_regions.append(
                    QuestionRegion(
                        question_number=r.question_number,
                        page_numbers=r.page_numbers,
                        text=r.text,
                        confidence=r.confidence,
                        status=SegmentationStatus.OUT_OF_ORDER,
                        lines=r.lines,
                    )
                )
            else:
                new_regions.append(r)
        regions = new_regions

    # Check for MISSING_QUESTION_NUMBER if expected_questions supplied
    if expected_questions:
        found_nums = {r.question_number for r in regions}
        for exp in expected_questions:
            if exp not in found_nums:
                regions.append(
                    QuestionRegion(
                        question_number=exp,
                        page_numbers=(),
                        text="",
                        confidence=None,
                        status=SegmentationStatus.MISSING_QUESTION_NUMBER,
                        lines=(),
                    )
                )

    logger.info("SEGMENTATION completed questions_found=%d", len(regions))
    return regions
