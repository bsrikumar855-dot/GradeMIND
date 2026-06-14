"""
Concept coverage engine for autonomous evaluation.

The engine uses deterministic keyword extraction, domain concept libraries, and
token overlap to infer expected concepts without requiring an answer key.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, List, Set


STOPWORDS = {
    "about", "above", "after", "again", "against", "answer", "because", "before",
    "below", "between", "compare", "define", "describe", "during", "each",
    "and", "explain", "from", "give", "have", "into", "list", "marks", "mention",
    "question", "semester", "show", "state", "that", "their", "there", "these", "this",
    "the", "through", "what", "when", "where", "which", "while", "with", "write",
    "why", "are", "was", "were",
    "sem", "biology", "chemistry", "physics", "mathematics", "maths", "science",
    "subject", "exam", "test",
}

CONCEPT_BLACKLIST = {
    "a", "an", "answer", "answer_key", "answers", "are", "coverage",
    "concept", "concepts", "expected", "expected_concepts", "is", "key",
    "key_concepts", "keys", "metadata", "the", "was", "were", "what",
    "when", "where", "why", "important",
}

GENERIC_LABELS = {
    "criteria", "description", "feedback", "field", "fields", "json", "label",
    "labels", "matched", "missing", "property", "rubric", "schema", "score",
    "student", "value", "values", "topic", "topics",
}

DOMAIN_CONCEPTS = {
    "biology": {
        "photosynthesis", "chlorophyll", "chloroplast", "sunlight", "carbon dioxide",
        "water", "glucose", "oxygen", "mitosis", "meiosis", "cell", "respiration",
        "enzyme", "protein", "dna", "organism", "plant",
    },
    "chemistry": {
        "atom", "molecule", "reaction", "bond", "acid", "base", "electron",
        "proton", "neutron", "oxidation", "reduction", "periodic", "catalyst",
        "solution", "compound",
    },
    "physics": {
        "force", "mass", "acceleration", "velocity", "energy", "work", "power",
        "momentum", "gravity", "wave", "current", "voltage", "resistance",
        "pressure", "motion",
    },
    "mathematics": {
        "equation", "variable", "coefficient", "constant", "derivative", "integral",
        "matrix", "probability", "function", "graph", "theorem", "proof", "angle",
        "triangle", "algebra",
    },
    "computer science": {
        "algorithm", "complexity", "data", "structure", "database", "network",
        "encryption", "function", "class", "object", "recursion", "array", "stack",
        "queue",
    },
}

SYNONYMS = {
    "carbon dioxide": {"co2", "carbon-dioxide"},
    "glucose": {"sugar"},
    "sunlight": {"light", "solar"},
    "chlorophyll": {"green pigment"},
    "oxygen": {"o2"},
    "water": {"h2o"},
    "equation": {"expression", "formula"},
    "photosynthesis": {"make food", "food making", "plants make food"},
}

IDENTITY_PATTERNS = [
    r"\bstudent\s*name\s*[:\-]\s*[A-Za-z .]+?(?=\s+(?:roll|id)\b|$)",
    r"\bname\s*[:\-]\s*[A-Za-z .]+?(?=\s+(?:roll|id)\b|$)",
    r"\broll\s*(?:no\.?|number)?\s*[:\-]?\s*[A-Za-z0-9_\-/]+",
    r"\bid\s*[:\-]\s*[A-Za-z0-9_\-/]+",
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
]

PROTECTED_TERMS = {
    "gender", "male", "female", "caste", "religion", "hindu", "muslim",
    "christian", "sikh", "school", "handwriting", "neatness",
}

CONCEPT_EXPANSIONS = {
    "photosynthesis": [
        "photosynthesis", "sunlight", "chlorophyll", "carbon dioxide",
        "water", "glucose", "oxygen",
    ],
}


class ConceptCoverageEngine:
    """Infer expected concepts and measure answer coverage."""

    def is_valid_concept(self, concept: str) -> bool:
        normalized = self.normalize_concept(concept)
        if len(normalized) < 3:
            return False
        if normalized in CONCEPT_BLACKLIST or normalized in GENERIC_LABELS:
            return False
        if normalized.replace(" ", "_") in CONCEPT_BLACKLIST:
            return False
        if normalized in STOPWORDS:
            return False
        return True

    def normalize_concept(self, concept: str) -> str:
        normalized = (concept or "").lower().strip()
        normalized = re.sub(r"^coverage of expected concept:\s*", "", normalized)
        normalized = normalized.replace("_", " ").replace("-", " ")
        normalized = re.sub(r"[^a-z0-9+ ]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def filter_concepts(self, concepts: List[str], limit: int | None = None) -> List[str]:
        filtered = []
        for concept in concepts:
            normalized = self.normalize_concept(concept)
            if self.is_valid_concept(normalized) and normalized not in filtered:
                filtered.append(normalized)
            if limit is not None and len(filtered) >= limit:
                break
        return filtered

    def sanitize_for_fairness(self, text: str) -> str:
        cleaned = text or ""
        for pattern in IDENTITY_PATTERNS:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        tokens = [
            token for token in cleaned.split()
            if token.strip(".,:;!?()[]{}").lower() not in PROTECTED_TERMS
        ]
        return re.sub(r"\s+", " ", " ".join(tokens)).strip()

    def extract_keywords(self, text: str, limit: int = 12) -> List[str]:
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+\-]{2,}\b", (text or "").lower())
        filtered = [
            self.normalize_concept(w.strip("-"))
            for w in words
            if w not in STOPWORDS and not w.isdigit()
        ]
        filtered = [w for w in filtered if self.is_valid_concept(w)]
        unique = list(dict.fromkeys(filtered))
        return unique[:limit]

    def infer_subject(self, question: str, subject: str = "") -> str:
        subject_lower = (subject or "").lower()
        if subject_lower:
            for domain in DOMAIN_CONCEPTS:
                if domain in subject_lower:
                    return domain

        question_lower = (question or "").lower()
        best_domain = ""
        best_hits = 0
        for domain, concepts in DOMAIN_CONCEPTS.items():
            hits = sum(1 for concept in concepts if concept in question_lower)
            if hits > best_hits:
                best_domain = domain
                best_hits = hits
        return best_domain

    def generate_expected_concepts(self, question: str, subject: str = "", max_concepts: int = 8) -> List[str]:
        if not question or not question.strip():
            raise ValueError("Question text is required for autonomous concept extraction.")

        question_lower = question.lower()
        concepts: List[str] = []
        domain = self.infer_subject(question, subject)
        if domain:
            for concept in DOMAIN_CONCEPTS[domain]:
                if concept in question_lower:
                    concepts.append(concept)
                    for related in CONCEPT_EXPANSIONS.get(concept, []):
                        if related not in concepts:
                            concepts.append(related)

        for keyword in self.extract_keywords(question, limit=max_concepts):
            if keyword not in concepts:
                concepts.append(keyword)

        concepts = self.filter_concepts(concepts, limit=max_concepts)

        if not concepts:
            raise ValueError("Unable to infer expected concepts from question text.")

        return concepts

    def _concept_present(self, concept: str, answer: str, answer_tokens: Set[str]) -> bool:
        concept_lower = concept.lower()
        if " " in concept_lower and concept_lower in answer:
            return True
        if concept_lower in answer_tokens or concept_lower in answer:
            return True
        for synonym in SYNONYMS.get(concept_lower, set()):
            if synonym in answer:
                return True
        return any(SequenceMatcher(None, concept_lower, token).ratio() >= 0.88 for token in answer_tokens)

    def evaluate_coverage(self, question: str, answer: str, subject: str = "") -> Dict[str, object]:
        sanitized_answer = self.sanitize_for_fairness(answer)
        expected = self.generate_expected_concepts(question, subject)
        answer_lower = sanitized_answer.lower()
        answer_tokens = set(self.extract_keywords(sanitized_answer, limit=200))

        expected = self.filter_concepts(expected)
        found = [concept for concept in expected if self._concept_present(concept, answer_lower, answer_tokens)]
        missing = [concept for concept in expected if concept not in found]
        coverage = (len(found) / len(expected) * 100.0) if expected else 0.0

        return {
            "expected_concepts": expected,
            "concepts_found": found,
            "concepts_missing": missing,
            "coverage_percentage": round(coverage, 2),
            "sanitized_answer": sanitized_answer,
        }

    def semantic_similarity(self, question: str, answer: str, subject: str = "") -> float:
        expected = set(self.filter_concepts(self.generate_expected_concepts(question, subject)))
        answer_terms = set(self.extract_keywords(self.sanitize_for_fairness(answer), limit=200))
        if not expected:
            return 0.0
        overlap = len(expected.intersection(answer_terms)) / len(expected)
        phrase_bonus = 0.1 if len(answer_terms) >= max(3, len(expected) // 2) else 0.0
        return round(min(1.0, overlap + phrase_bonus), 2)
