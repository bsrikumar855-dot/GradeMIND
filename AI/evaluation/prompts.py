"""
Prompt templates for GradeMIND autonomous evaluation.

These prompts document the LLM contract used by the autonomous evaluator. The
current implementation is deterministic and local, but keeps the prompt surface
stable for a future provider-backed scorer.
"""

AUTONOMOUS_SCORING_PROMPT = """
You are an experienced board examiner.

Question:
{question}

Maximum Marks:
{marks}

Student Answer:
{answer}

Instructions:
1. Determine what concepts are required.
2. Infer expected learning outcomes.
3. Evaluate conceptual correctness.
4. Evaluate completeness.
5. Ignore handwriting quality.
6. Ignore grammar mistakes.
7. Ignore spelling mistakes unless they change meaning.
8. Reward partial understanding.
9. Reward correct reasoning.
10. Penalize factual errors.

Return JSON only.
{{
  "marks_awarded": 0,
  "max_marks": 0,
  "confidence": 0,
  "concept_coverage": [],
  "missing_concepts": [],
  "strengths": [],
  "weaknesses": [],
  "feedback": ""
}}
""".strip()

CONCEPT_COVERAGE_PROMPT = """
Identify the expected concepts for the question and compare them with the
student answer. Ignore identity, handwriting, grammar, and spelling unless the
meaning changes.

Question: {question}
Student Answer: {answer}

Return JSON only with concepts_found, concepts_missing, and coverage_percentage.
""".strip()

FEEDBACK_GENERATION_PROMPT = """
Generate concise student-facing feedback from the scoring result. Include
strengths, weaknesses, improvements, and study recommendations.

Question: {question}
Score: {score}/{max_marks}
Missing Concepts: {missing_concepts}
Found Concepts: {found_concepts}
""".strip()
