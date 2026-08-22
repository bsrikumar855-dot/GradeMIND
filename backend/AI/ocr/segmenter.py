"""
GradeMIND Question Segmenter.
Segments text lines from OCR output into logical question-answer blocks based on structural patterns.
"""

import re
import logging
from typing import Dict, List, Tuple
from AI.schemas.ocr_schema import OCRDocument, OCRLine

logger = logging.getLogger("GradeMIND.Segmenter")


def identify_question_numbers(text: str) -> List[Tuple[str, int]]:
    """
    Identifies question indicators and their start index inside a text block.
    Matches Q1, 1., Question 1, (a), (b), (i), (ii).
    
    Args:
        text: The complete text string to analyze.
        
    Returns:
        List of tuples containing (matched_header_label, char_start_index).
    """
    # Regex patterns for matching common headers
    patterns = [
        r"\b(?:Q|Question|Q\.)\s*(\d+)\b",                # Q1, Question 2, Q.3
        r"\n\s*(\d+)\s*[\.\)]\s",                           # 1. or 2) at beginning of line
        r"\b\(([a-zA-Z])\)\s",                              # (a) or (b)
        r"\b\(([ivxIVX]+)\)\s"                              # (i) or (ii)
    ]
    
    found = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            found.append((match.group(0).strip(), match.start()))
            
    # Sort matches by their starting character index
    found.sort(key=lambda x: x[1])
    return found


def group_answer_blocks(lines: List[OCRLine]) -> Dict[str, List[OCRLine]]:
    """
    Groups visual lines of OCR output by their nearest preceding question label.
    
    Args:
        lines: List of OCRLine objects sorted in reading order.
        
    Returns:
        Dictionary mapping question label keys (e.g. 'question_1') to list of text lines.
    """
    # Main headers: Q1, Question 1, 1.
    main_q_pattern = re.compile(r"^\s*(?:Q|Question|Q\.)\s*(\d+)|^\s*(\d+)\s*[\.\)]", re.IGNORECASE)
    # Sub-headers: (a), (b)
    sub_q_pattern = re.compile(r"^\s*\(([a-zA-Z])\)", re.IGNORECASE)
    # Sub-sub-headers: (i), (ii)
    roman_q_pattern = re.compile(r"^\s*\(([ivxIVX]+)\)", re.IGNORECASE)

    grouped: Dict[str, List[OCRLine]] = {}
    current_q = "header"  # Fallback for text before any question label
    
    for line in lines:
        text_strip = line.text.strip()
        
        main_match = main_q_pattern.match(text_strip)
        sub_match = sub_q_pattern.match(text_strip)
        roman_match = roman_q_pattern.match(text_strip)
        
        # Determine if line initiates a new block
        if main_match:
            q_num = main_match.group(1) or main_match.group(2)
            current_q = f"question_{q_num}"
        elif sub_match:
            sub_char = sub_match.group(1)
            # If sub-question belongs to a main question, combine them (e.g., question_1_a)
            if "question_" in current_q:
                # Strip previous sub-level to prevent compounding (e.g., question_1_a_b)
                base_q = re.split(r"_[a-zA-Z]$", current_q)[0]
                # Strip roman level too if any
                base_q = re.split(r"_[ivxIVX]+$", base_q)[0]
                current_q = f"{base_q}_{sub_char.lower()}"
            else:
                current_q = f"question_{sub_char.lower()}"
        elif roman_match:
            roman_val = roman_match.group(1)
            if "question_" in current_q:
                base_q = re.split(r"_[ivxIVX]+$", current_q)[0]
                current_q = f"{base_q}_{roman_val.lower()}"
            else:
                current_q = f"question_{roman_val.lower()}"
                
        if current_q not in grouped:
            grouped[current_q] = []
            
        grouped[current_q].append(line)
        
    return grouped


def segment_questions(ocr_document: OCRDocument) -> Dict[str, str]:
    """
    Segments the OCRDocument lines into a map of question labels and text responses.
    
    Args:
        ocr_document: Fully processed OCRDocument.
        
    Returns:
        Dict mapping question identifiers (e.g., 'question_1') to full text string.
    """
    if not ocr_document.lines:
        logger.warning("OCR Document contains no lines to segment.")
        return {}

    # Group the line objects
    grouped_blocks = group_answer_blocks(ocr_document.lines)
    
    # Format line lists into consolidated strings
    segmented_text: Dict[str, str] = {}
    for q_label, lines in grouped_blocks.items():
        if q_label == "header":
            # Skip page headers or titles unless they are requested
            continue
            
        # Join the text lines
        full_text = " ".join(line.text.strip() for line in lines)
        
        # Clean up double spacing and normalize
        full_text = re.sub(r"\s+", " ", full_text).strip()
        segmented_text[q_label] = full_text

    logger.info(f"Segmented OCRDocument into {len(segmented_text)} question answers: {list(segmented_text.keys())}")
    return segmented_text
