"""
Parser for the Gemini Evaluation Layer.
Handles malformed JSON, markdown fences, and schema validation.
"""

import json
import logging
import re
from typing import Dict, Any, Optional

from AI.schemas.evaluation_schema import GeminiEvaluation

logger = logging.getLogger("GradeMIND.GeminiParser")

class GeminiParser:
    """
    Robust parser to extract GeminiEvaluation from raw text.
    Never crashes; returns None on irrecoverable failures.
    """

    @classmethod
    def parse(cls, raw_response: str, model_name: str) -> Optional[GeminiEvaluation]:
        if not raw_response or not raw_response.strip():
            logger.warning("Empty response from Gemini.")
            return None

        # Clean markdown wrappers (e.g. ```json ... ```)
        cleaned_text = cls._strip_markdown_fences(raw_response)

        try:
            # Parse JSON
            data = json.loads(cleaned_text)
            
            # Ensure it's a dict
            if not isinstance(data, dict):
                logger.warning("Gemini response parsed to non-dictionary type.")
                return None
            
            # Inject the model name
            data["model"] = model_name
            
            # Validate schema
            return GeminiEvaluation(**data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}\nRaw output: {raw_response[:200]}...")
            return None
        except Exception as e:
            # Catch Pydantic validation errors or anything else
            logger.error(f"Failed to validate GeminiEvaluation schema: {e}")
            return None

    @classmethod
    def _strip_markdown_fences(cls, text: str) -> str:
        """Removes markdown code block delimiters and surrounding whitespace."""
        text = text.strip()
        # Regex to match ```json (or just ```) at start, and ``` at end
        pattern = r"^```(?:json)?\s*(.*?)\s*```$"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text
