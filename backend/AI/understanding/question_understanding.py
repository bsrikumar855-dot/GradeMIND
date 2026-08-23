"""
GradeMIND Question Understanding Agent.
Extracts intent, topics, keywords, and classifies question types using NLP heuristics.
Supports optional LLM integrations for enhanced processing.
"""

import re
import os
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger("GradeMIND.QuestionUnderstanding")

# Simple list of English stopwords for keyword extraction
STOPWORDS = {
    "what", "is", "are", "the", "a", "an", "and", "or", "but", "if", "then",
    "of", "to", "in", "on", "at", "by", "for", "with", "about", "against",
    "during", "before", "after", "above", "below", "from", "up", "down",
    "in", "out", "over", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "s", "t", "can", "will",
    "just", "don", "should", "now", "define", "explain", "compare", "list",
    "describe", "contrast", "distinguish", "calculate", "solve", "find",
    "sketch", "draw", "label", "identify", "meaning"
}


class QuestionUnderstandingAgent:
    """
    Agent responsible for analyzing the question prompt to identify key concepts,
    intent, topics, and classification types.
    """
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm and bool(os.getenv("GEMINI_API_KEY"))

    def detect_question_type(self, question_text: str) -> str:
        """
        Classify the question into one of: Definition, Explanation, Comparison, List, Diagram, Numerical.
        
        Args:
            question_text: Raw text of the question.
            
        Returns:
            The classified question type string.
        """
        q_lower = question_text.lower()
        
        # Rule 1: Comparison
        if any(w in q_lower for w in ["compare", "contrast", "difference between", "distinguish", "difference"]):
            return "comparison"
            
        # Rule 2: Diagram
        if any(w in q_lower for w in ["draw", "diagram", "label", "sketch", "graph", "plot"]):
            return "diagram"
            
        # Rule 3: Numerical
        if any(w in q_lower for w in ["calculate", "solve", "evaluate", "find the value", "compute", "equation"]):
            return "numerical"
            
        # Rule 4: List
        if any(w in q_lower for w in ["list", "name", "state", "enumerate", "give 3", "give 5", "mention"]):
            return "list"
            
        # Rule 5: Definition
        if any(w in q_lower for w in ["define", "what is", "what are", "meaning of", "definition"]):
            return "definition"
            
        # Default classification
        return "explanation"

    def extract_keywords(self, question_text: str) -> List[str]:
        """
        Extract key terms from the question by removing punctuation and stopwords.
        
        Args:
            question_text: Raw text of the question.
            
        Returns:
            List of keywords.
        """
        # Normalize and split words, removing non-alphabetic chars
        words = re.findall(r"\b[a-zA-Z]{3,}\b", question_text.lower())
        keywords = [w for w in words if w not in STOPWORDS]
        # De-duplicate while preserving order
        return list(dict.fromkeys(keywords))

    def extract_topics(self, question_text: str) -> List[str]:
        """
        Map extracted keywords and context to broader topic domains.
        
        Args:
            question_text: Raw text of the question.
            
        Returns:
            List of topics/subject domains.
        """
        q_lower = question_text.lower()
        topics = []
        
        # Simple domain classifier dictionary
        domain_mapping = {
            "biology": ["mitosis", "meiosis", "photosynthesis", "chloroplast", "cell", "organelle", "chlorophyll", "plant"],
            "chemistry": ["reaction", "element", "molecule", "bond", "periodic", "acid", "base", "ph"],
            "mathematics": ["solve", "equation", "x =", "y =", "calculus", "limit", "integral", "derivative", "algebra"],
            "physics": ["force", "energy", "velocity", "gravity", "mass", "motion", "wave", "optics"]
        }
        
        for topic_domain, indicators in domain_mapping.items():
            if any(ind in q_lower for ind in indicators):
                topics.append(topic_domain.capitalize())
                
        # Fallback topic
        if not topics:
            keywords = self.extract_keywords(question_text)
            topics = [kw.capitalize() for kw in keywords[:2]] if keywords else ["General"]
            
        return topics

    def extract_intent(self, question_text: str) -> str:
        """
        Synthesize the core objective of the question into a structured intent sentence.
        
        Args:
            question_text: Raw text of the question.
            
        Returns:
            A descriptive intent string.
        """
        q_type = self.detect_question_type(question_text)
        keywords = self.extract_keywords(question_text)
        keywords_str = ", ".join(keywords[:3])
        
        if q_type == "comparison":
            return f"Compare and contrast concepts related to: {keywords_str}."
        elif q_type == "definition":
            return f"Define and explain the meaning of: {keywords_str}."
        elif q_type == "numerical":
            return f"Perform calculations or solve mathematical problem for: {keywords_str}."
        elif q_type == "list":
            return f"Enumerate or list items/characteristics of: {keywords_str}."
        elif q_type == "diagram":
            return f"Sketch and label a diagram demonstrating: {keywords_str}."
        else:
            return f"Explain the mechanisms or details concerning: {keywords_str}."

    def analyze_question(self, question_text: str) -> Dict[str, Any]:
        """
        Full understanding pipeline. If use_llm is enabled, it attempts to use a model,
        otherwise it runs the local heuristic NLP pipeline.
        
        Args:
            question_text: Raw text of the question.
            
        Returns:
            A dictionary containing intent, topics, keywords, and question_type.
        """
        if self.use_llm:
            try:
                # Optional LLM path is intentionally disabled until a provider client is configured.
                pass
            except Exception as e:
                logger.error(f"LLM question understanding failed, falling back to heuristics: {e}")
                
        # Rule-based analysis
        q_type = self.detect_question_type(question_text)
        keywords = self.extract_keywords(question_text)
        topics = self.extract_topics(question_text)
        intent = self.extract_intent(question_text)
        
        return {
            "intent": intent,
            "topics": topics,
            "keywords": keywords,
            "question_type": q_type
        }
