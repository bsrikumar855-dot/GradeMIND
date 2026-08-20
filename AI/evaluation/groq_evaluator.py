"""
GradeMIND Groq AI Evaluator. DISABLED BY DEFAULT. See below before re-enabling.

THIS CLASS TAKES THE MARK FROM AN LLM AND THAT CANNOT SATISFY RULE 3.

Master spec rule 3 requires every mark awarded to be traceable to three things:
a marking-scheme criterion id, a character span in the extracted answer text,
and the engine version that produced it. This evaluator produces none of them.
It prompts a model with:

    "1. Assign a fair score_awarded between 0.0 and {max_marks}"

and then lifts the number straight out of the reply:

    score = min(max(float(parsed.get("score_awarded", 0.0)), 0.0), max_marks)

There is no scheme, no evidence span, and no arithmetic. The number cannot be
re-derived later from stored evidence, so it cannot survive an appeal: asked
why a student got 3.5, the only truthful answer is "a language model said so
on a Tuesday".

Two further properties make it worse than merely untraceable:

  * `parsed.get("score_awarded", 0.0)` DEFAULTS TO ZERO. A reply that omits
    the key marks the candidate zero, and nothing distinguishes that from a
    model that read the answer and judged it worth nothing. That is the
    silent-zero defect Phase 0 removed from the OCR path, re-entering through
    the evaluator.
  * `parsed.get("confidence", 0.95)` DEFAULTS TO 0.95, so a missing field
    becomes high confidence in a fabricated mark.

WHAT THIS CLASS IS STILL GOOD FOR. Nothing above says an LLM has no place
here. It says an LLM may not be the authority on a number. Extracting
evidence, paraphrasing, classifying, and explaining are all legitimate work
for the language layer, and `extract_evidence` is the shape that work should
take: the model finds the span, and deterministic arithmetic decides the mark.
That is why this file is kept rather than deleted, and why the full pipeline
is preserved on `archive/groq-baidu-pipeline`.

TO RE-ENABLE, deliberately: set GROQ_ALLOW_LLM_MARKING=true. Construction
raises otherwise. Any mark it produces is undefensible on appeal and must
never reach a student.
"""

from __future__ import annotations

import json
import logging
import os
import requests
from typing import Any, Dict, List, Optional

from AI.schemas.evaluation_schema import QuestionEvaluation, RubricCriterion

logger = logging.getLogger("GradeMIND.GroqEvaluator")

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
FALLBACK_GROQ_MODEL = "qwen/qwen3.6-27b"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMMarkingDisabled(RuntimeError):
    """Raised when something tries to build an evaluator that marks by LLM.

    A distinct type so a caller can catch exactly this and route to
    MANDATORY_HUMAN, rather than swallowing it in a bare `except Exception`
    and silently producing no mark at all.
    """


class GroqEvaluator:
    """
    Expert AI Evaluator powered by Groq LLM API.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        # Refuse at CONSTRUCTION, not at evaluate(). A class that can be built
        # and only fails when it marks something is one code path away from
        # marking something.
        if os.environ.get("GROQ_ALLOW_LLM_MARKING", "").strip().lower() != "true":
            raise LLMMarkingDisabled(
                "GroqEvaluator is disabled. It takes score_awarded from an LLM "
                "reply, which cannot satisfy master spec rule 3: no criterion "
                "id, no evidence span, no arithmetic, and no way to re-derive "
                "the mark on appeal. It also defaults a missing score to 0.0 "
                "and a missing confidence to 0.95. Set "
                "GROQ_ALLOW_LLM_MARKING=true to override, and read this "
                "module's docstring before you do. The full pipeline is "
                "preserved on branch archive/groq-baidu-pipeline."
            )

        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            # Try loading from backend/.env if available
            try:
                from dotenv import load_dotenv
                from pathlib import Path
                env_path = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"
                if env_path.exists():
                    load_dotenv(dotenv_path=env_path)
                self.api_key = os.environ.get("GROQ_API_KEY")
            except Exception:
                pass
        
        self.model = model or os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    def is_available(self) -> bool:
        """Returns True if Groq API key is present."""
        return bool(self.api_key)

    def evaluate(
        self,
        question: str,
        student_answer: str,
        max_marks: float,
        question_number: str = "1",
        reference_answer: Optional[str] = None,
        subject: str = "",
    ) -> QuestionEvaluation:
        """
        Evaluates student answer using 120B parameter LLM via Groq API.
        """
        if not self.is_available():
            raise RuntimeError("GROQ_API_KEY is not set.")

        prompt = f"""You are a master academic examiner evaluating a student's answer.
Analyze the question and student response with extreme rigor, fairness, and precision.

Subject/Context: {subject or 'General / Academic'}
Question #{question_number}: {question}
Maximum Marks: {max_marks}
{f"Reference Answer / Marking Scheme: {reference_answer}" if reference_answer else "Evaluation Mode: Autonomous Expert Assessment"}

Student's Answer:
\"\"\"{student_answer or '(No answer provided)'}\"\"\"

Instructions:
1. Assign a fair score_awarded between 0.0 and {max_marks} (can use half-marks e.g. 3.5).
2. List 2-4 key concepts/keywords found in the student's response ('matched_concepts').
3. List any missing key concepts required for a full-mark answer ('missing_concepts').
4. Breakdown marks into 2-4 rubric criteria with criterion_id, description, allocated_marks, and marks_awarded.
5. Provide concise, constructive feedback: strengths, weaknesses, and improvement suggestions.

Respond ONLY with valid JSON in this exact structure:
{{
  "score_awarded": float,
  "confidence": float,
  "matched_concepts": [string],
  "missing_concepts": [string],
  "rubric_points": [
    {{
      "criterion_id": string,
      "description": string,
      "allocated_marks": float,
      "marks_awarded": float,
      "met": boolean
    }}
  ],
  "strengths": [string],
  "weaknesses": [string],
  "improvements": [string],
  "evaluator_summary": string
}}
"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise, objective automated academic grading system. Output pure valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            res = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=12)
            if res.status_code != 200:
                logger.warning("Groq primary model %s failed (%s). Retrying with %s...", self.model, res.status_code, FALLBACK_GROQ_MODEL)
                payload["model"] = FALLBACK_GROQ_MODEL
                res = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=12)

            res.raise_for_status()
            res_json = res.json()
            raw_content = res_json['choices'][0]['message']['content']
            parsed = json.loads(raw_content)

            # Build Pydantic RubricCriteria
            rubric_points = []
            for idx, pt in enumerate(parsed.get("rubric_points", []), 1):
                rubric_points.append(
                    RubricCriterion(
                        criterion_id=pt.get("criterion_id", f"c_{idx}"),
                        description=pt.get("description", "Evaluation criterion"),
                        allocated_marks=float(pt.get("allocated_marks", max_marks / max(1, len(parsed.get("rubric_points", []))))),
                        marks_awarded=float(pt.get("marks_awarded", 0.0)),
                        met=bool(pt.get("met", False))
                    )
                )

            score = min(max(float(parsed.get("score_awarded", 0.0)), 0.0), max_marks)
            conf = min(max(float(parsed.get("confidence", 0.95)), 0.0), 1.0)
            matched = [str(c).strip() for c in parsed.get("matched_concepts", []) if c]
            missing = [str(c).strip() for c in parsed.get("missing_concepts", []) if c]

            feedback_str = (
                f"Groq 120B AI Evaluator Score: {score}/{max_marks}. "
                f"Strengths: {', '.join(parsed.get('strengths', ['Valid response']))}. "
                f"Missing: {', '.join(missing) if missing else 'None'}."
            )

            return QuestionEvaluation(
                question_number=question_number,
                max_marks=max_marks,
                score_awarded=score,
                student_answer_extracted=student_answer or "",
                criteria_feedback=feedback_str,
                matched_keywords=matched,
                rubric_points=rubric_points,
                confidence=conf,
                concept_coverage=round((len(matched) / max(1, len(matched) + len(missing))) * 100.0, 2),
                missing_concepts=missing,
                evaluation_mode="AI_AUTONOMOUS" if not reference_answer else "ANSWER_KEY",
            )

        except Exception as exc:
            logger.exception("GroqEvaluator call failed for Q%s: %s", question_number, exc)
            raise exc
