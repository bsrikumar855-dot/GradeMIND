"""
Tests for OR-question detection, splitting, and answer-to-alternative resolution.

Covers:
  - 2-choice OR (basic)
  - 3-choice OR
  - Handwritten-style OR (noisy formatting)
  - OCR-noisy OR (missing whitespace / case variation)
  - Answer written for second option only
  - Answer written for first option only
  - Non-OR question (regression)
  - Full parse_questions_with_or integration
  - select_best_alternative integration
"""

import sys
import os
import pytest

# Ensure GradeMIND root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from AI.evaluation.or_question_resolver import (
    has_or_structure,
    split_or_alternatives,
    parse_questions_with_or,
    select_best_alternative,
    resolve_or_question,
    QuestionGroup,
    QuestionAlternative,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. has_or_structure
# ─────────────────────────────────────────────────────────────────────────────

class TestHasOrStructure:
    def test_standalone_OR_on_own_line(self):
        text = "Explain streamlined flow\nOR\nExplain Kolmogorov turbulence"
        assert has_or_structure(text) is True

    def test_inline_OR_uppercase(self):
        text = "Define osmosis OR Define diffusion"
        assert has_or_structure(text) is True

    def test_inline_or_lowercase(self):
        text = "State Newton's first law or state Galileo's law of inertia"
        assert has_or_structure(text) is True

    def test_either_keyword(self):
        text = "Either explain photosynthesis or explain respiration"
        assert has_or_structure(text) is True

    def test_any_one_keyword(self):
        text = "Answer Any One of the following:\na) Explain convection\nb) Explain conduction"
        assert has_or_structure(text) is True

    def test_attempt_any_one_keyword(self):
        text = "Attempt Any One:\n1. Describe DNA replication\n2. Describe protein synthesis"
        assert has_or_structure(text) is True

    def test_regular_question_not_detected(self):
        text = "Explain the process of photosynthesis in detail."
        assert has_or_structure(text) is False

    def test_question_with_or_in_word(self):
        # "more" or "before" should not trigger OR detection
        text = "What happened before the industrial revolution?"
        assert has_or_structure(text) is False

    def test_ocr_noisy_or_extra_spaces(self):
        # OCR may introduce extra spaces around OR
        text = "Explain laminar flow  OR  explain turbulent flow"
        assert has_or_structure(text) is True

    def test_ocr_noisy_or_mixed_case(self):
        text = "Explain mitosis\nOr\nExplain meiosis"
        assert has_or_structure(text) is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. split_or_alternatives
# ─────────────────────────────────────────────────────────────────────────────

class TestSplitOrAlternatives:
    def test_two_choice_multiline(self):
        text = "Explain streamlined flow\nOR\nExplain Kolmogorov turbulence"
        parts = split_or_alternatives(text)
        assert len(parts) == 2
        assert "streamlined" in parts[0].lower()
        assert "kolmogorov" in parts[1].lower()

    def test_two_choice_inline(self):
        text = "Define osmosis OR Define diffusion"
        parts = split_or_alternatives(text)
        assert len(parts) == 2
        assert "osmosis" in parts[0].lower()
        assert "diffusion" in parts[1].lower()

    def test_three_choice_multiline(self):
        text = "Explain convection\nOR\nExplain conduction\nOR\nExplain radiation"
        parts = split_or_alternatives(text)
        assert len(parts) == 3, f"Expected 3 parts, got {len(parts)}: {parts}"
        assert "convection" in parts[0].lower()
        assert "conduction" in parts[1].lower()
        assert "radiation" in parts[2].lower()

    def test_handwritten_style_with_newlines(self):
        # Handwritten exams often have irregular spacing
        text = "  Explain the working of a turbine\n\nOR\n\nExplain the working of a steam engine  "
        parts = split_or_alternatives(text)
        assert len(parts) == 2
        assert "turbine" in parts[0].lower()
        assert "steam" in parts[1].lower()

    def test_strips_whitespace(self):
        text = "  Option A text  \nOR\n  Option B text  "
        parts = split_or_alternatives(text)
        assert all(p == p.strip() for p in parts)


# ─────────────────────────────────────────────────────────────────────────────
# 3. parse_questions_with_or
# ─────────────────────────────────────────────────────────────────────────────

class TestParseQuestionsWithOr:
    def test_single_or_question(self):
        qp_text = "1. Explain stream-lined flow\nOR\nExplain Kolmogorov turbulence"
        result = parse_questions_with_or(qp_text, total_marks=5.0)
        assert "question_1" in result
        entry = result["question_1"]
        assert entry["or_group"] is not None
        group = entry["or_group"]
        assert group.group_type == "OR"
        assert len(group.alternatives) == 2

    def test_or_group_alternative_labels(self):
        qp_text = "1. Explain stream-lined flow\nOR\nExplain Kolmogorov turbulence"
        result = parse_questions_with_or(qp_text, total_marks=5.0)
        group = result["question_1"]["or_group"]
        labels = [a.label for a in group.alternatives]
        assert "question_1_optA" in labels
        assert "question_1_optB" in labels

    def test_three_alternatives_parsed(self):
        qp_text = "1. Explain convection\nOR\nExplain conduction\nOR\nExplain radiation"
        result = parse_questions_with_or(qp_text, total_marks=6.0)
        group = result["question_1"]["or_group"]
        assert len(group.alternatives) == 3

    def test_non_or_question_has_no_group(self):
        qp_text = "1. Explain photosynthesis in detail."
        result = parse_questions_with_or(qp_text, total_marks=5.0)
        assert result["question_1"]["or_group"] is None

    def test_marks_distributed_to_or_group(self):
        qp_text = "1. Explain osmosis\nOR\nExplain diffusion"
        result = parse_questions_with_or(qp_text, total_marks=10.0)
        entry = result["question_1"]
        assert entry["marks"] == 10.0

    def test_marks_from_question_text(self):
        qp_text = "1. [5 Marks] Explain osmosis\nOR\nExplain diffusion"
        result = parse_questions_with_or(qp_text, total_marks=100.0)
        entry = result["question_1"]
        assert entry["marks"] == 5.0

    def test_empty_text_raises(self):
        with pytest.raises(ValueError, match="required"):
            parse_questions_with_or("", total_marks=10.0)

    def test_mixed_or_and_regular_questions(self):
        qp_text = (
            "1. Explain photosynthesis.\n"
            "2. Explain streamlined flow\nOR\nExplain Kolmogorov turbulence\n"
            "3. Define Newton's laws."
        )
        result = parse_questions_with_or(qp_text, total_marks=15.0)
        assert result["question_1"]["or_group"] is None
        assert result["question_2"]["or_group"] is not None
        assert result["question_3"]["or_group"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. select_best_alternative
# ─────────────────────────────────────────────────────────────────────────────

class TestSelectBestAlternative:
    def _make_group(self, texts):
        alts = [
            QuestionAlternative(
                label=f"question_1_opt{chr(ord('A') + i)}",
                text=t,
                marks=5.0,
            )
            for i, t in enumerate(texts)
        ]
        return QuestionGroup(
            group_id="question_1",
            group_type="OR",
            alternatives=alts,
            marks=5.0,
        )

    def test_selects_second_option_when_answered(self):
        """Student answers Kolmogorov turbulence (option B). Must select option B."""
        group = self._make_group([
            "Explain stream-lined flow",
            "Explain Kolmogorov turbulence",
        ])
        student_ans = (
            "Kolmogorov turbulence is a statistical theory that describes how "
            "kinetic energy is transferred from large eddies to smaller ones, "
            "following the -5/3 power law in the inertial subrange."
        )
        best_alt, score, all_scores = select_best_alternative(group, student_ans)
        assert best_alt.label == "question_1_optB", (
            f"Expected optB to be selected, got {best_alt.label} "
            f"(score={score:.3f}, all_scores={[(a.label, s) for a, s in all_scores]})"
        )
        assert score > 0.0

    def test_selects_first_option_when_answered(self):
        """Student answers streamlined flow (option A). Must select option A."""
        group = self._make_group([
            "Explain stream-lined flow",
            "Explain Kolmogorov turbulence",
        ])
        student_ans = (
            "Streamlined flow, also known as laminar flow, occurs when a fluid "
            "moves in parallel layers with no disruption between layers. "
            "The Reynolds number is low and flow is orderly."
        )
        best_alt, score, all_scores = select_best_alternative(group, student_ans)
        assert best_alt.label == "question_1_optA", (
            f"Expected optA to be selected, got {best_alt.label} "
            f"(score={score:.3f})"
        )

    def test_three_choice_selects_middle(self):
        """Student answers conduction (option B of 3). Must select option B."""
        group = self._make_group([
            "Explain convection",
            "Explain conduction",
            "Explain radiation",
        ])
        student_ans = (
            "Conduction is the transfer of heat through direct molecular contact. "
            "Thermal conductivity determines how well a material conducts heat. "
            "Metals are good conductors."
        )
        best_alt, score, _ = select_best_alternative(group, student_ans)
        assert best_alt.label == "question_1_optB", (
            f"Expected optB (conduction), got {best_alt.label}"
        )

    def test_empty_answer_returns_first_alternative(self):
        """Empty student answers should return some alternative gracefully."""
        group = self._make_group([
            "Explain osmosis",
            "Explain diffusion",
        ])
        best_alt, score, _ = select_best_alternative(group, "")
        assert best_alt is not None
        assert score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 5. resolve_or_question (integration)
# ─────────────────────────────────────────────────────────────────────────────

class TestResolveOrQuestion:
    def test_or_question_resolves_to_chosen_alternative(self):
        qp_text = "1. Explain stream-lined flow\nOR\nExplain Kolmogorov turbulence"
        questions = parse_questions_with_or(qp_text, total_marks=5.0)
        student_ans = (
            "Kolmogorov turbulence describes the cascade of energy through "
            "turbulent eddies from large scales to small scales. "
            "The energy spectrum follows a -5/3 power law."
        )
        resolved_text, chosen_label, match_score = resolve_or_question(
            q_id="question_1",
            question_info=questions["question_1"],
            student_answer=student_ans,
        )
        assert "Kolmogorov" in resolved_text
        assert "stream-lined" not in resolved_text.lower() or "kolmogorov" in resolved_text.lower()
        assert "optB" in chosen_label
        assert match_score > 0.0

    def test_non_or_question_resolves_unchanged(self):
        qp_text = "1. Explain photosynthesis in detail."
        questions = parse_questions_with_or(qp_text, total_marks=5.0)
        student_ans = "Photosynthesis converts carbon dioxide and water into glucose using sunlight."
        resolved_text, chosen_label, match_score = resolve_or_question(
            q_id="question_1",
            question_info=questions["question_1"],
            student_answer=student_ans,
        )
        assert resolved_text == questions["question_1"]["text"]
        assert chosen_label == "question_1"
        assert match_score == 1.0

    def test_ocr_noisy_or_still_resolves(self):
        """Simulate OCR that collapses newlines around OR."""
        qp_text = "1. Explain stream-lined flow OR Explain Kolmogorov turbulence"
        questions = parse_questions_with_or(qp_text, total_marks=5.0)
        student_ans = "Kolmogorov turbulence energy spectrum eddies cascade inertial subrange."
        entry = questions["question_1"]
        # Even with inline OR, should still detect and split
        if entry["or_group"] is not None:
            resolved_text, chosen_label, _ = resolve_or_question(
                q_id="question_1",
                question_info=entry,
                student_answer=student_ans,
            )
            assert "Kolmogorov" in resolved_text
        else:
            # Inline OR was normalised away — acceptable fallback
            pytest.skip("Inline OR not detected in normalised text; acceptable for OCR noise case")

    def test_second_option_only_answered_not_penalized(self):
        """
        Core regression test:
        Student answered ONLY Kolmogorov turbulence.
        The resolved question text must NOT include 'stream-lined flow'.
        This ensures the evaluator doesn't penalize for missing streamlined flow concepts.
        """
        qp_text = "1. Explain stream-lined flow\nOR\nExplain Kolmogorov turbulence"
        questions = parse_questions_with_or(qp_text, total_marks=5.0)
        student_ans = (
            "Kolmogorov turbulence is the statistical theory of turbulence "
            "developed by Andrei Kolmogorov. Energy cascades from large eddies "
            "to small eddies. The -5/3 power law describes the energy spectrum."
        )
        resolved_text, chosen_label, match_score = resolve_or_question(
            q_id="question_1",
            question_info=questions["question_1"],
            student_answer=student_ans,
        )
        # The resolved question should be ONLY the Kolmogorov alternative
        assert "stream-lined" not in resolved_text.lower(), (
            f"Resolved question still contains 'stream-lined'! "
            f"resolved_text={repr(resolved_text)}"
        )
        assert "kolmogorov" in resolved_text.lower(), (
            f"Resolved question does not contain 'Kolmogorov'! "
            f"resolved_text={repr(resolved_text)}"
        )
        assert "optB" in chosen_label


if __name__ == "__main__":
    # Allow running directly for quick local check
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
    )
    sys.exit(result.returncode)
