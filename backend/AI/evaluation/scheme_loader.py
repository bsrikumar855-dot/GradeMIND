"""Marking scheme JSON loader.

Deserializes scheme JSON into SchemeQuestion and ValuePoint dataclasses.
Ensures exact field name matching and enum conversions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from AI.evaluation.value_point import GroupRule, MatchMode, SchemeQuestion, ValuePoint


def load_marking_scheme(path: str | Path) -> List[SchemeQuestion]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Marking scheme file not found: {p}")

    data = json.loads(p.read_text(encoding="utf-8"))
    questions_raw = data.get("questions", data) if isinstance(data, dict) else data

    questions: List[SchemeQuestion] = []
    for q_dict in questions_raw:
        vps: List[ValuePoint] = []
        for vp_dict in q_dict["value_points"]:
            match_mode = MatchMode(vp_dict.get("match_mode", "EXACT"))
            group_rule = GroupRule(vp_dict["group_rule"]) if vp_dict.get("group_rule") else None

            vp = ValuePoint(
                id=vp_dict["id"],
                text=vp_dict["text"],
                marks=float(vp_dict["marks"]),
                acceptable_variants=tuple(vp_dict.get("acceptable_variants", ())),
                match_mode=match_mode,
                group_id=vp_dict.get("group_id"),
                group_rule=group_rule,
                group_n=vp_dict.get("group_n"),
                expected_value=float(vp_dict["expected_value"]) if vp_dict.get("expected_value") is not None else None,
                tolerance=float(vp_dict["tolerance"]) if vp_dict.get("tolerance") is not None else None,
                unit=vp_dict.get("unit"),
            )
            vps.append(vp)

        sq = SchemeQuestion(
            id=q_dict["id"],
            question_number=str(q_dict["question_number"]),
            question_text=q_dict["question_text"],
            max_marks=float(q_dict["max_marks"]),
            value_points=tuple(vps),
        )
        questions.append(sq)

    return questions
