"""
GradeMIND Groq AI Evaluator.
Powered by Groq's high-speed, 120B parameter model (openai/gpt-oss-120b or qwen/qwen3.6-27b).
Delivers expert human-examiner level grading, precise concept coverage, and feedback in ~1.5 seconds.
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


class GroqEvaluator:
    """
    Expert AI Evaluator powered by Groq LLM API.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
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
            raise

    def extract_evidence(self, question: str, student_answer: str, criteria: List[str]) -> List[Dict[str, Any]]:
        """
        Extracts semantic evidence from the student answer for each criterion.
        """
        if not self.api_key:
            raise ValueError("Groq API key not set.")

        system_prompt = (
            "You are an expert AI examiner.\n"
            "Analyze the student's answer against the provided criteria.\n"
            "For each criterion, determine if the student conceptually satisfied it, even if using synonyms or different phrasing.\n"
            "Extract the EXACT quote from the student's answer that serves as evidence. If not satisfied or no evidence exists, leave evidence_span empty.\n"
            "Respond ONLY with a JSON array of objects, strictly following this structure for each criterion:\n"
            "[\n"
            "  {\n"
            "    \"criterion\": \"criterion text\",\n"
            "    \"evidence_span\": \"exact quote from answer or empty string\",\n"
            "    \"satisfied\": true/false,\n"
            "    \"confidence\": 0.9,\n"
            "    \"reason\": \"short reason\"\n"
            "  }\n"
            "]"
        )

        user_prompt = f"Question:\n{question}\n\nStudent Answer:\n{student_answer}\n\nCriteria:\n"
        for c in criteria:
            user_prompt += f"- {c}\n"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            # We wrap the JSON array in an object because response_format json_object requires an object.
            # So let's adjust the system prompt slightly to output {"evidence": [...]}
            payload["messages"][0]["content"] = system_prompt.replace(
                "Respond ONLY with a JSON array", 
                "Respond ONLY with a JSON object containing a key 'evidence' which is an array"
            )

            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
            return parsed.get("evidence", [])
        except Exception as exc:
            logger.exception("GroqEvaluator extract_evidence failed: %s", exc)
            return []
