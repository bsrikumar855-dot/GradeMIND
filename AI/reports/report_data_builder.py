"""
GradeMIND Report Data Builder.
Prepares structured data payloads for PDF Generation, Analytics,
Teacher Dashboards, and Student Dashboards from evaluation outputs.
"""

import logging
import math
import os
import shutil
import subprocess
import tempfile
from typing import List, Dict, Any
from AI.schemas.evaluation_schema import SubmissionEvaluation

logger = logging.getLogger("GradeMIND.ReportBuilder")


class ReportDataBuilder:
    """
    Compiler of specialized reporting models for various presentation channels.
    """
    def __init__(self):
        pass

    def build_pdf_payload(self, evaluation: SubmissionEvaluation) -> Dict[str, Any]:
        """
        Builds a layout-ready dictionary structure for PDF generation.
        
        Args:
            evaluation: SubmissionEvaluation Pydantic model.
            
        Returns:
            Dictionary containing structured layout fields.
        """
        logger.info(f"Building PDF payload for submission {evaluation.submission_id}")
        
        question_rows = []
        for q in evaluation.questions:
            question_rows.append({
                "question_number": q.question_number,
                "max_marks": q.max_marks,
                "score_awarded": q.score_awarded,
                "confidence": f"{q.confidence:.2%}",
                "feedback": q.criteria_feedback,
                "concept_coverage": q.concept_coverage,
                "evaluation_mode": q.evaluation_mode or evaluation.evaluation_mode
            })

        return {
            "document_title": f"GradeMIND Evaluation Report Card",
            "submission_id": evaluation.submission_id,
            "status": evaluation.status,
            "overall_summary": {
                "total_score": evaluation.total_score,
                "max_possible": evaluation.max_possible,
                "percentage": f"{(evaluation.total_score / evaluation.max_possible * 100):.1f}%" if evaluation.max_possible > 0 else "0.0%",
                "confidence_score": f"{evaluation.confidence_score:.2%}",
                "fairness_index": f"{evaluation.fairness_score:.2%}",
                "evaluation_mode": evaluation.evaluation_mode,
                "concept_coverage": evaluation.concept_coverage
            },
            "grading_breakdown": question_rows,
            "constructive_feedback": {
                "strengths": evaluation.strengths,
                "weaknesses": evaluation.weaknesses,
                "improvements": evaluation.improvements,
                "study_recommendations": evaluation.study_recommendations,
                "summary": evaluation.summary
            }
        }

    def build_analytics(self, evaluations: List[SubmissionEvaluation]) -> Dict[str, Any]:
        """
        Compiles aggregate statistics across a cohort of submissions.
        
        Args:
            evaluations: List of SubmissionEvaluation objects.
            
        Returns:
            Analytics dictionary containing class metrics.
        """
        if not evaluations:
            return {
                "total_submissions": 0,
                "class_average": 0.0,
                "highest_score": 0.0,
                "lowest_score": 0.0,
                "distribution": {
                    "90-100": 0, "80-89": 0, "70-79": 0, "60-69": 0, "below_60": 0
                }
            }

        total_submissions = len(evaluations)
        scores = []
        highest = 0.0
        lowest = float('inf')
        
        distribution = {
            "90-100": 0,
            "80-89": 0,
            "70-79": 0,
            "60-69": 0,
            "below_60": 0
        }

        for eval_item in evaluations:
            total = eval_item.total_score
            max_p = eval_item.max_possible
            percentage = (total / max_p * 100.0) if max_p > 0 else 0.0
            
            scores.append(percentage)
            
            if total > highest:
                highest = total
            if total < lowest:
                lowest = total

            # Categorize brackets
            if percentage >= 90:
                distribution["90-100"] += 1
            elif percentage >= 80:
                distribution["80-89"] += 1
            elif percentage >= 70:
                distribution["70-79"] += 1
            elif percentage >= 60:
                distribution["60-69"] += 1
            else:
                distribution["below_60"] += 1

        lowest = lowest if lowest != float('inf') else 0.0
        class_average = sum(scores) / total_submissions if total_submissions > 0 else 0.0

        return {
            "total_submissions": total_submissions,
            "class_average": round(class_average, 2),
            "highest_score": round(highest, 2),
            "lowest_score": round(lowest, 2),
            "distribution": distribution
        }

    def build_teacher_dashboard(self, evaluations: List[SubmissionEvaluation]) -> Dict[str, Any]:
        """
        Prepares dashboard views for course instructors.
        Identifies submissions requiring manual override/review.
        
        Args:
            evaluations: List of SubmissionEvaluation objects.
            
        Returns:
            Teacher dashboard data structure.
        """
        submissions_summary = []
        review_required = []

        for eval_item in evaluations:
            pct = (eval_item.total_score / eval_item.max_possible * 100.0) if eval_item.max_possible > 0 else 0.0
            
            summary_entry = {
                "submission_id": eval_item.submission_id,
                "score_awarded": eval_item.total_score,
                "max_possible": eval_item.max_possible,
                "percentage": round(pct, 2),
                "confidence_score": eval_item.confidence_score,
                "evaluation_mode": eval_item.evaluation_mode,
                "status": eval_item.status
            }
            
            submissions_summary.append(summary_entry)
            
            # Review flag conditions: Low AI confidence (< 0.70) or fairness failures
            if eval_item.confidence_score < 0.70 or not eval_item.fairness_verified or eval_item.status == "PENDING_REVIEW":
                review_required.append({
                    "submission_id": eval_item.submission_id,
                    "reason": (
                        "Low AI Confidence" if eval_item.confidence_score < 0.70 else "Fairness Check Warning"
                    ),
                    "confidence_score": eval_item.confidence_score
                })

        # Calculate cohort average
        analytics_summary = self.build_analytics(evaluations)

        return {
            "total_students": len(evaluations),
            "class_average_percentage": analytics_summary["class_average"],
            "submissions": submissions_summary,
            "review_queue": review_required,
            "review_queue_count": len(review_required),
            "score_distribution": analytics_summary["distribution"]
        }

    def build_student_dashboard(self, evaluation: SubmissionEvaluation) -> Dict[str, Any]:
        """
        Prepares diagnostic dashboard views customized for the student.
        
        Args:
            evaluation: SubmissionEvaluation object.
            
        Returns:
            Student dashboard data structure.
        """
        percentage = (evaluation.total_score / evaluation.max_possible * 100.0) if evaluation.max_possible > 0 else 0.0
        
        # Build question list
        question_grades = []
        for q in evaluation.questions:
            q_pct = (q.score_awarded / q.max_marks * 100.0) if q.max_marks > 0 else 0.0
            question_grades.append({
                "question_number": q.question_number,
                "score": q.score_awarded,
                "max_marks": q.max_marks,
                "percentage": round(q_pct, 2),
                "feedback": q.criteria_feedback,
                "concept_coverage": q.concept_coverage
            })

        return {
            "submission_id": evaluation.submission_id,
            "score_awarded": evaluation.total_score,
            "max_possible": evaluation.max_possible,
            "score_percentage": round(percentage, 2),
            "strengths": evaluation.strengths,
            "improvements": evaluation.improvements,
            "study_recommendations": evaluation.study_recommendations,
            "summary_comment": evaluation.summary,
            "questions_grades": question_grades
        }

    def generate_pdf_report(
        self,
        evaluation: SubmissionEvaluation,
        output_path: str,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        """
        Generates a premium LaTeX-based AI assessment report.
        """
        logger.info(f"Generating PDF report file at {output_path}")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        latex_source = self.render_latex_report(evaluation, metadata=metadata)
        tex_path = os.path.splitext(output_path)[0] + ".tex"
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_source)
        logger.info("LaTeX source written: tex_path=%s output_path=%s", tex_path, output_path)

        if self._compile_latex(tex_path, output_path):
            logger.info("LaTeX PDF compiled successfully: output_path=%s", output_path)
            return

        logger.warning(
            "LaTeX compilation unavailable or failed. Returning fallback PDF while preserving LaTeX source: %s",
            tex_path,
        )
        self._generate_fallback_pdf(evaluation, output_path, metadata=metadata)

    def render_latex_report(
        self,
        evaluation: SubmissionEvaluation,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        """Render a reusable LaTeX report template from evaluation JSON."""
        meta = self._report_metrics(evaluation, metadata=metadata)
        questions = evaluation.questions or []
        strengths = evaluation.strengths or ["Shows willingness to attempt the assessment."]
        weaknesses = evaluation.weaknesses or ["No major weak area was detected."]
        improvements = evaluation.improvements or ["Continue practicing structured answers."]
        study_topics = evaluation.study_recommendations or ["Core Concepts From This Assessment"]
        covered_concepts, missing_concepts = self._concept_lists(evaluation)

        return "\n".join([
            self._latex_preamble(),
            r"\begin{document}",
            self._cover_page(meta, evaluation),
            self._performance_overview(meta, evaluation),
            self._question_breakdown(questions),
            self._concept_analysis(covered_concepts, missing_concepts, evaluation),
            self._strengths_weaknesses(strengths, weaknesses),
            self._study_plan(study_topics, improvements, missing_concepts),
            self._analytics(meta),
            self._teacher_insights(evaluation, improvements),
            self._detailed_feedback(questions),
            self._final_summary(meta, strengths, weaknesses, study_topics),
            r"\end{document}",
        ])

    def _latex_preamble(self) -> str:
        return r"""
\documentclass[10pt]{article}
\usepackage[margin=0.55in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage{xcolor}
\usepackage{tikz}
\usepackage{pgfplots}
\usepackage[most]{tcolorbox}
\usepackage{fancyhdr}
\usepackage{qrcode}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{array}
\usepackage{colortbl}
\usepackage{longtable}
\usepackage{multicol}
\usepackage{enumitem}
\usepackage{pifont}
\usepackage{hyperref}
\pgfplotsset{compat=1.18}
\usetikzlibrary{positioning,calc,shadows.blur}
\definecolor{gmgreen}{HTML}{7FB77E}
\definecolor{gmdark}{HTML}{2D5A3D}
\definecolor{gmblue}{HTML}{5B8DEF}
\definecolor{gmlight}{HTML}{F6FBF5}
\definecolor{gmsoftblue}{HTML}{EEF4FF}
\definecolor{gmred}{HTML}{F87171}
\definecolor{gmyellow}{HTML}{F8C65A}
\hypersetup{colorlinks=true, linkcolor=gmdark, urlcolor=gmblue}
\pagestyle{fancy}
\fancyhf{}
\lhead{\textcolor{gmdark}{\textbf{GradeMIND AI Assessment Report}}}
\rhead{\textcolor{gmgreen}{\thepage}}
\renewcommand{\headrulewidth}{0.3pt}
\setlength{\parindent}{0pt}
\setlist[itemize]{leftmargin=*, itemsep=2pt, topsep=2pt}
\newtcolorbox{gmcard}[2][]{enhanced, colback=white, colframe=#2, arc=4mm, boxrule=0.8pt, left=4mm, right=4mm, top=3mm, bottom=3mm, drop shadow, #1}
\newtcolorbox{kpicard}[2][]{enhanced, colback=#2!8, colframe=#2, arc=4mm, boxrule=0.7pt, left=3mm, right=3mm, top=2mm, bottom=2mm, #1}
\newcommand{\checkmarkgm}{\textcolor{gmgreen}{\ding{51}}}
\newcommand{\crossgm}{\textcolor{gmred}{\ding{55}}}
"""

    def _cover_page(self, meta: Dict[str, Any], evaluation: SubmissionEvaluation) -> str:
        verification = self._latex_escape(
            f"GradeMIND:{evaluation.submission_id}:score={meta['score_text']}:confidence={meta['confidence_pct']}%"
        )
        return rf"""
\begin{{titlepage}}
\pagecolor{{gmlight}}
\begin{{tikzpicture}}[remember picture,overlay]
  \fill[gmgreen!18] (current page.north west) rectangle ([yshift=-3.2cm]current page.north east);
  \fill[gmblue!12] ([xshift=-2cm,yshift=-18cm]current page.north east) circle (7cm);
  \fill[gmgreen!18] ([xshift=2cm,yshift=2cm]current page.south west) circle (6cm);
\end{{tikzpicture}}
\vspace*{{0.4cm}}
\includegraphics[width=2.6cm]{{{self._latex_image_path(meta['logo_path'])}}}\\[0.25cm]
{{\Huge\bfseries\textcolor{{gmdark}}{{GradeMIND}}}}\\[0.2cm]
{{\Large\textcolor{{gmblue}}{{Premium AI Assessment Report}}}}\\[1.0cm]
\begin{{gmcard}}{{gmgreen}}
  \begin{{tabularx}}{{\textwidth}}{{X r}}
    {{\LARGE\bfseries\textcolor{{gmdark}}{{{self._latex_escape(meta['student_name'])}}}}} &
    \qrcode[height=2.2cm]{{{verification}}}\\
    \textcolor{{gray}}{{Exam}}: \textbf{{{self._latex_escape(meta['exam_name'])}}} &
    \textcolor{{gray}}{{QR Verification}}\\
  \end{{tabularx}}
\end{{gmcard}}
\vspace{{0.7cm}}
\begin{{center}}
\begin{{tikzpicture}}
  \node[draw=gmgreen, fill=white, rounded corners=16pt, line width=1pt, minimum width=5.2cm, minimum height=3.5cm, blur shadow] (score) {{
    \begin{{tabular}}{{c}}
      \Huge\bfseries\textcolor{{gmdark}}{{{meta['score_text']}}}\\
      \textcolor{{gray}}{{Overall Score}}
    \end{{tabular}}
  }};
  \node[draw=gmblue, fill=white, rounded corners=16pt, line width=1pt, minimum width=4.0cm, minimum height=3.5cm, right=0.5cm of score, blur shadow] {{
    \begin{{tabular}}{{c}}
      \Huge\bfseries\textcolor{{gmblue}}{{{meta['grade']}}}\\
      \textcolor{{gray}}{{Grade}}
    \end{{tabular}}
  }};
\end{{tikzpicture}}
\end{{center}}
\vspace{{0.5cm}}
\begin{{multicols}}{{2}}
\begin{{kpicard}}{{gmgreen}}\textbf{{AI Confidence}}\\{{\Large {meta['confidence_pct']}\%}}\end{{kpicard}}
\begin{{kpicard}}{{gmblue}}\textbf{{Concept Coverage}}\\{{\Large {meta['coverage_pct']}\%}}\end{{kpicard}}
\end{{multicols}}
\vfill
\begin{{center}}
\textcolor{{gmdark}}{{Generated by GradeMIND AI Evaluation Engine}}\\
\textcolor{{gray}}{{Commercial-ready assessment analytics for students, teachers, and institutions}}
\end{{center}}
\end{{titlepage}}
\nopagecolor
"""

    def _performance_overview(self, meta: Dict[str, Any], evaluation: SubmissionEvaluation) -> str:
        coords = " ".join(
            f"({self._latex_escape(str(q.question_number))},{q.score_awarded})"
            for q in evaluation.questions
        ) or "(NoData,0)"
        max_marks = max([q.max_marks for q in evaluation.questions] + [evaluation.max_possible, 1])
        return rf"""
\section*{{1. Performance Overview}}
\begin{{multicols}}{{4}}
\begin{{kpicard}}{{gmgreen}}\textbf{{Score}}\\{{\Large {meta['score_text']}}}\end{{kpicard}}
\begin{{kpicard}}{{gmblue}}\textbf{{Grade}}\\{{\Large {meta['grade']}}}\end{{kpicard}}
\begin{{kpicard}}{{gmgreen}}\textbf{{AI Confidence}}\\{{\Large {meta['confidence_pct']}\%}}\end{{kpicard}}
\begin{{kpicard}}{{gmblue}}\textbf{{Coverage}}\\{{\Large {meta['coverage_pct']}\%}}\end{{kpicard}}
\end{{multicols}}
\begin{{gmcard}}{{gmblue}}
\textbf{{Question-wise Marks}}\\[2mm]
\begin{{tikzpicture}}
\begin{{axis}}[
  ybar, bar width=12pt, width=\textwidth, height=6cm,
  ymin=0, ymax={max_marks + 1},
  symbolic x coords={{{','.join(self._latex_escape(str(q.question_number)) for q in evaluation.questions) or 'NoData'}}},
  xtick=data, ylabel={{Marks}}, xlabel={{Question}},
  nodes near coords, nodes near coords align={{vertical}},
  grid=major, grid style={{draw=gray!12}},
  axis line style={{draw=gray!30}},
  tick style={{draw=none}},
  every node near coord/.append style={{font=\scriptsize}},
  fill=gmgreen
]
\addplot coordinates {{{coords}}};
\end{{axis}}
\end{{tikzpicture}}
\end{{gmcard}}
"""

    def _question_breakdown(self, questions: List[Any]) -> str:
        rows = []
        for idx, q in enumerate(questions):
            coverage = q.concept_coverage if q.concept_coverage is not None else self._question_percentage(q)
            shade = "gmgreen!9" if self._question_percentage(q) >= 75 else ("gmyellow!12" if self._question_percentage(q) >= 45 else "gmred!8")
            rows.append(
                rf"\rowcolor{{{shade}}} Q{self._latex_escape(str(q.question_number))} & "
                rf"{q.score_awarded:g}/{q.max_marks:g} & {coverage:.0f}\% & "
                rf"\footnotesize {self._latex_escape(q.criteria_feedback or 'No AI remark available.')} \\"
            )
        body = "\n".join(rows) or r"\rowcolor{gray!8} -- & -- & -- & No question rows available. \\"
        return rf"""
\section*{{2. Question Breakdown}}
\begin{{longtable}}{{>{{\bfseries}}p{{0.12\textwidth}} p{{0.16\textwidth}} p{{0.16\textwidth}} p{{0.48\textwidth}}}}
\toprule
Question & Marks & Coverage & AI Remarks\\
\midrule
{body}
\bottomrule
\end{{longtable}}
"""

    def _concept_analysis(self, covered: List[str], missing: List[str], evaluation: SubmissionEvaluation) -> str:
        covered_items = self._latex_items(covered[:16], check=True, empty="No covered concepts were detected.")
        missing_items = self._latex_items(missing[:16], check=False, empty="No missing concepts were detected.")
        observation = evaluation.summary or "GradeMIND analyzed the response for conceptual accuracy, explanation depth, and rubric alignment."
        return rf"""
\section*{{3. Concept Analysis}}
\begin{{multicols}}{{2}}
\begin{{gmcard}}{{gmgreen}}
\textbf{{Covered Concepts}}\\
\begin{{itemize}}{covered_items}\end{{itemize}}
\end{{gmcard}}
\begin{{gmcard}}{{gmred}}
\textbf{{Missing Concepts}}\\
\begin{{itemize}}{missing_items}\end{{itemize}}
\end{{gmcard}}
\end{{multicols}}
\begin{{gmcard}}{{gmblue}}
\textbf{{AI Observation}}\\
{self._latex_escape(observation)}
\end{{gmcard}}
"""

    def _strengths_weaknesses(self, strengths: List[str], weaknesses: List[str]) -> str:
        return rf"""
\section*{{4. Strengths vs Weak Areas}}
\begin{{multicols}}{{2}}
\begin{{gmcard}}{{gmgreen}}
\textbf{{Strengths}}\\
\begin{{itemize}}{self._latex_items(strengths[:8], check=True)}\end{{itemize}}
\end{{gmcard}}
\begin{{gmcard}}{{gmred}}
\textbf{{Weak Areas}}\\
\begin{{itemize}}{self._latex_items(weaknesses[:8], check=False)}\end{{itemize}}
\end{{gmcard}}
\end{{multicols}}
"""

    def _study_plan(self, topics: List[str], improvements: List[str], missing: List[str]) -> str:
        high = missing[:4] or topics[:2]
        medium = topics[2:6] or improvements[:4]
        low = topics[6:10] or ["Timed practice", "Answer presentation", "Revision notes"]
        return rf"""
\section*{{5. Personalized Study Plan}}
\begin{{multicols}}{{3}}
\begin{{gmcard}}{{gmred}}\textbf{{High Priority}}\\\begin{{itemize}}{self._latex_items(high, bullet='--')}\end{{itemize}}\end{{gmcard}}
\begin{{gmcard}}{{gmblue}}\textbf{{Medium Priority}}\\\begin{{itemize}}{self._latex_items(medium, bullet='--')}\end{{itemize}}\end{{gmcard}}
\begin{{gmcard}}{{gmgreen}}\textbf{{Low Priority}}\\\begin{{itemize}}{self._latex_items(low, bullet='--')}\end{{itemize}}\end{{gmcard}}
\end{{multicols}}
\begin{{gmcard}}{{gmblue}}
\textbf{{Actionable Recommendations}}\\
\begin{{itemize}}{self._latex_items(improvements[:8], bullet='--')}\end{{itemize}}
\end{{gmcard}}
"""

    def _analytics(self, meta: Dict[str, Any]) -> str:
        radar = self._radar_chart(meta)
        doughnut = self._doughnut_chart(meta["percentage"])
        return rf"""
\section*{{6. Analytics}}
\begin{{multicols}}{{2}}
\begin{{gmcard}}{{gmblue}}
\textbf{{Radar Profile}}\\[2mm]
{radar}
\end{{gmcard}}
\begin{{gmcard}}{{gmgreen}}
\textbf{{Score Doughnut}}\\[2mm]
{doughnut}
\end{{gmcard}}
\end{{multicols}}
\begin{{gmcard}}{{gmgreen}}
\textbf{{Coverage Metrics}}\\
Score {meta['percentage']}\%, AI Confidence {meta['confidence_pct']}\%, Concept Coverage {meta['coverage_pct']}\%, Fairness Index {meta['fairness_pct']}\%.
\end{{gmcard}}
"""

    def _teacher_insights(self, evaluation: SubmissionEvaluation, improvements: List[str]) -> str:
        narrative = evaluation.summary or "The submission was evaluated across marks, conceptual coverage, confidence, and feedback quality."
        return rf"""
\section*{{7. Teacher Insights}}
\begin{{gmcard}}{{gmdark}}
\textbf{{Professional Narrative Summary}}\\
{self._latex_escape(narrative)}\\[2mm]
\textbf{{Improvement Suggestions}}\\
\begin{{itemize}}{self._latex_items(improvements[:8], bullet='--')}\end{{itemize}}
\end{{gmcard}}
"""

    def _detailed_feedback(self, questions: List[Any]) -> str:
        cards = []
        for q in questions:
            cards.append(rf"""
\begin{{gmcard}}{{gmblue}}
\textbf{{Question {self._latex_escape(str(q.question_number))}}} \hfill {q.score_awarded:g}/{q.max_marks:g}\\
{self._latex_escape(q.criteria_feedback or 'No detailed feedback available.')}
\end{{gmcard}}
""")
        return "\\section*{8. Detailed AI Feedback}\n" + ("\n".join(cards) or "No detailed feedback rows available.")

    def _final_summary(self, meta: Dict[str, Any], strengths: List[str], weaknesses: List[str], topics: List[str]) -> str:
        return rf"""
\section*{{9. Final Summary}}
\begin{{gmcard}}{{gmgreen}}
\begin{{tabularx}}{{\textwidth}}{{l X}}
\textbf{{Overall Grade}} & {meta['grade']}\\
\textbf{{Top Strength}} & {self._latex_escape(strengths[0] if strengths else 'Consistent effort')}\\
\textbf{{Improvement Area}} & {self._latex_escape(weaknesses[0] if weaknesses else 'Advanced practice')}\\
\textbf{{Recommended Next Topic}} & {self._latex_escape(topics[0] if topics else 'Core revision')}\\
\textbf{{AI Confidence}} & {meta['confidence_pct']}\%\\
\textbf{{QR Verification}} & \qrcode[height=1.2cm]{{{self._latex_escape('GradeMIND:' + str(meta['submission_id']))}}}\\
\end{{tabularx}}
\end{{gmcard}}
"""

    def _report_metrics(
        self,
        evaluation: SubmissionEvaluation,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        metadata = metadata or {}
        max_possible = evaluation.max_possible or 0.0
        percentage = (evaluation.total_score / max_possible * 100.0) if max_possible > 0 else 0.0
        coverage_values = [q.concept_coverage for q in evaluation.questions if q.concept_coverage is not None]
        coverage = evaluation.concept_coverage if evaluation.concept_coverage is not None else (
            sum(coverage_values) / len(coverage_values) if coverage_values else percentage
        )
        logo_path = metadata.get("logo_path") or os.path.join(
            os.path.dirname(__file__),
            "assets",
            "grademind-logo-official.jpeg",
        )
        return {
            "submission_id": str(evaluation.submission_id),
            "logo_path": logo_path,
            "student_name": metadata.get("student_name") or metadata.get("studentName") or "Student",
            "exam_name": metadata.get("exam_name") or metadata.get("exam_title") or metadata.get("examTitle") or "Assessment",
            "score_text": f"{evaluation.total_score:g}/{max_possible:g}",
            "percentage": round(percentage, 1),
            "grade": self._grade_for_percentage(percentage),
            "confidence_pct": round((evaluation.confidence_score or 0.0) * 100, 1),
            "coverage_pct": round(coverage, 1),
            "fairness_pct": round((evaluation.fairness_score or 0.0) * 100, 1),
        }

    def _compile_latex(self, tex_path: str, output_path: str) -> bool:
        compiler = self._latex_compiler()
        if not compiler:
            logger.error(
                "LaTeX compiler missing. Install pdflatex, xelatex, or lualatex and ensure it is available on PATH. "
                "tex_path=%s output_path=%s",
                tex_path,
                output_path,
            )
            return False
        output_dir = os.path.dirname(os.path.abspath(output_path))
        base_name = os.path.splitext(os.path.basename(tex_path))[0]
        logger.info(
            "Starting LaTeX compilation: compiler=%s tex_path=%s output_path=%s output_dir=%s",
            compiler,
            tex_path,
            output_path,
            output_dir,
        )
        with tempfile.TemporaryDirectory(dir=output_dir) as tmpdir:
            tmp_tex = os.path.join(tmpdir, os.path.basename(tex_path))
            shutil.copyfile(tex_path, tmp_tex)
            command = self._latex_command(compiler, tmpdir, tmp_tex)
            logger.info("LaTeX compiler command: %s", " ".join(command))
            for attempt in range(1, 3):
                logger.info("Running LaTeX compiler attempt %s/2", attempt)
                result = subprocess.run(command, capture_output=True, text=True, timeout=90)
                logger.info(
                    "LaTeX compiler attempt %s finished: returncode=%s stdout=%s stderr=%s",
                    attempt,
                    result.returncode,
                    result.stdout[-8000:],
                    result.stderr[-8000:],
                )
                if result.returncode != 0:
                    logger.error(
                        "LaTeX compilation failed on attempt %s. compiler=%s tex_path=%s command=%s",
                        attempt,
                        compiler,
                        tex_path,
                        " ".join(command),
                    )
                    return False
            built_pdf = os.path.join(tmpdir, base_name + ".pdf")
            if os.path.exists(built_pdf):
                shutil.copyfile(built_pdf, output_path)
                logger.info("Compiled LaTeX PDF copied: built_pdf=%s output_path=%s", built_pdf, output_path)
                return True
            logger.error(
                "LaTeX compiler completed without producing expected PDF: expected_pdf=%s tex_path=%s",
                built_pdf,
                tex_path,
            )
        return False

    def _latex_compiler(self) -> str | None:
        for compiler in ("pdflatex", "xelatex", "lualatex"):
            found = shutil.which(compiler)
            if found:
                logger.info("LaTeX compiler discovered: %s=%s", compiler, found)
                return found
        miktex_bin = os.path.join(
            os.path.expanduser("~"),
            "AppData",
            "Local",
            "Programs",
            "MiKTeX",
            "miktex",
            "bin",
            "x64",
        )
        for compiler in ("miktex-pdftex.exe", "miktex-xetex.exe", "miktex-luatex.exe"):
            candidate = os.path.join(miktex_bin, compiler)
            if os.path.exists(candidate):
                logger.info("MiKTeX compiler engine discovered: %s", candidate)
                return candidate
        logger.error("No LaTeX compiler discovered on PATH. Checked: pdflatex, xelatex, lualatex")
        return None

    def _latex_command(self, compiler: str, output_dir: str, tex_path: str) -> List[str]:
        compiler_name = os.path.basename(compiler).lower()
        alias = None
        if compiler_name == "miktex-pdftex.exe":
            alias = "pdflatex"
        elif compiler_name == "miktex-xetex.exe":
            alias = "xelatex"
        elif compiler_name == "miktex-luatex.exe":
            alias = "lualatex"

        command = [compiler]
        if alias:
            command.append(f"-undump={alias}")
            command.append("-enable-installer")
        command.extend([
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={output_dir}",
            tex_path,
        ])
        return command

    def _concept_lists(self, evaluation: SubmissionEvaluation) -> tuple[List[str], List[str]]:
        covered = []
        missing = []
        for q in evaluation.questions:
            covered.extend(q.matched_keywords or [])
            missing.extend(q.missing_concepts or [])
            for point in q.rubric_points or []:
                description = point.description.replace("Coverage of expected concept:", "").strip()
                if point.met:
                    covered.append(description)
                else:
                    missing.append(description)
        return self._unique_clean(covered), self._unique_clean(missing)

    def _unique_clean(self, values: List[str]) -> List[str]:
        result = []
        seen = set()
        for value in values:
            clean = " ".join(str(value or "").split()).strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                result.append(clean)
        return result

    def _radar_chart(self, meta: Dict[str, Any]) -> str:
        values = [
            ("Score", meta["percentage"]),
            ("Confidence", meta["confidence_pct"]),
            ("Coverage", meta["coverage_pct"]),
            ("Fairness", meta["fairness_pct"]),
            ("Readiness", (meta["percentage"] + meta["coverage_pct"]) / 2),
        ]
        points = []
        labels = []
        for idx, (label, value) in enumerate(values):
            angle = math.radians(90 + idx * 360 / len(values))
            radius = max(0.0, min(100.0, value)) / 100 * 2.2
            points.append(f"({radius * math.cos(angle):.2f},{radius * math.sin(angle):.2f})")
            labels.append((label, 2.65 * math.cos(angle), 2.65 * math.sin(angle)))
        label_nodes = "\n".join(
            rf"\node[font=\scriptsize] at ({x:.2f},{y:.2f}) {{{self._latex_escape(label)}}};"
            for label, x, y in labels
        )
        return rf"""
\begin{{center}}
\begin{{tikzpicture}}[scale=1.0]
  \foreach \r in {{0.55,1.10,1.65,2.20}} \draw[gray!20] (0,0) circle (\r);
  \foreach \a in {{90,162,234,306,18}} \draw[gray!25] (0,0) -- (\a:2.3);
  \filldraw[fill=gmblue!22, draw=gmblue, line width=1pt] {' -- '.join(points)} -- cycle;
  {label_nodes}
\end{{tikzpicture}}
\end{{center}}
"""

    def _doughnut_chart(self, percentage: float) -> str:
        pct = max(0.0, min(100.0, percentage))
        end_angle = 90 - (pct / 100 * 360)
        return rf"""
\begin{{center}}
\begin{{tikzpicture}}
  \draw[line width=18pt, gray!15] (0,0) circle (1.55cm);
  \draw[line width=18pt, gmgreen] (90:1.55cm) arc (90:{end_angle:.1f}:1.55cm);
  \node[align=center] at (0,0) {{\Huge\bfseries\textcolor{{gmdark}}{{{pct:.0f}\%}}\\\scriptsize Score}};
\end{{tikzpicture}}
\end{{center}}
"""

    def _latex_items(self, items: List[str], check: bool | None = None, bullet: str | None = None, empty: str = "No items available.") -> str:
        if not items:
            items = [empty]
        rows = []
        for item in items:
            marker = ""
            if check is True:
                marker = r"\checkmarkgm\ "
            elif check is False:
                marker = r"\crossgm\ "
            elif bullet:
                marker = f"{bullet} "
            rows.append(rf"\item {marker}{self._latex_escape(item)}")
        return "\n".join(rows)

    def _question_percentage(self, question: Any) -> float:
        return (question.score_awarded / question.max_marks * 100.0) if question.max_marks else 0.0

    def _grade_for_percentage(self, percentage: float) -> str:
        if percentage >= 90:
            return "A+"
        if percentage >= 80:
            return "A"
        if percentage >= 70:
            return "B"
        if percentage >= 60:
            return "C"
        if percentage >= 50:
            return "D"
        return "F"

    def _latex_escape(self, value: Any) -> str:
        text = str(value if value is not None else "")
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        return "".join(replacements.get(char, char) for char in text)

    def _latex_image_path(self, value: Any) -> str:
        return str(value if value is not None else "").replace("\\", "/").replace("{", "").replace("}", "")

    def _generate_fallback_pdf(
        self,
        evaluation: SubmissionEvaluation,
        output_path: str,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        try:
            self._generate_premium_reportlab_pdf(evaluation, output_path, metadata=metadata)
            return
        except Exception as exc:
            logger.exception("Premium ReportLab fallback failed. Writing basic fallback PDF: %s", exc)

        metadata = metadata or {}
        student_name = metadata.get("student_name") or metadata.get("studentName") or "Student"
        percentage = (evaluation.total_score / evaluation.max_possible * 100) if evaluation.max_possible else 0
        lines = [
            "GradeMIND Premium AI Assessment Report",
            f"Student: {student_name}",
            f"Submission ID: {evaluation.submission_id}",
            f"Score: {evaluation.total_score:g}/{evaluation.max_possible:g}",
            f"Grade: {self._grade_for_percentage(percentage)}",
            f"Percentage: {percentage:.1f}%",
            f"AI Confidence: {(evaluation.confidence_score or 0) * 100:.1f}%",
            f"Concept Coverage: {(evaluation.concept_coverage if evaluation.concept_coverage is not None else percentage):.1f}%",
            f"Fairness Index: {(evaluation.fairness_score or 0) * 100:.1f}%",
            "",
            "Teacher Summary",
            evaluation.summary or "The response was evaluated across score, confidence, concept coverage, and feedback quality.",
            "",
            "Strengths",
            *[f"- {item}" for item in (evaluation.strengths or ["Shows willingness to attempt the assessment."])],
            "",
            "Weak Areas",
            *[f"- {item}" for item in (evaluation.weaknesses or ["No major weak area was detected."])],
            "",
            "Personalized Study Plan",
            *[f"- {item}" for item in (evaluation.study_recommendations or evaluation.improvements or ["Continue practicing structured answers."])],
            "",
            "Question-wise AI Feedback",
        ]
        for question in evaluation.questions:
            coverage = question.concept_coverage if question.concept_coverage is not None else self._question_percentage(question)
            lines.extend([
                "",
                f"Question {question.question_number}: {question.score_awarded:g}/{question.max_marks:g} marks, coverage {coverage:.0f}%",
                question.criteria_feedback or "No detailed feedback available.",
            ])
            if question.missing_concepts:
                lines.append("Missing concepts: " + ", ".join(str(item) for item in question.missing_concepts[:8]))
        logger.info("Writing functional fallback PDF report: output_path=%s lines=%s", output_path, len(lines))
        self._write_basic_pdf(lines, output_path)

    def _generate_premium_reportlab_pdf(
        self,
        evaluation: SubmissionEvaluation,
        output_path: str,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Image,
            KeepTogether,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.graphics.shapes import Circle, Drawing, Rect, String, Wedge

        logger.info("Generating premium ReportLab PDF fallback: output_path=%s", output_path)

        gm_green = colors.HexColor("#7FB77E")
        gm_dark = colors.HexColor("#2D5A3D")
        gm_blue = colors.HexColor("#5B8DEF")
        gm_light = colors.HexColor("#F6FBF5")
        gm_soft_blue = colors.HexColor("#EEF4FF")
        gm_red = colors.HexColor("#F87171")
        gm_yellow = colors.HexColor("#F8C65A")
        page_width, page_height = A4

        meta = self._report_metrics(evaluation, metadata=metadata)
        questions = evaluation.questions or []
        strengths = evaluation.strengths or ["Shows consistent effort and readiness to improve."]
        weaknesses = evaluation.weaknesses or ["No major weak area was detected."]
        improvements = evaluation.improvements or ["Continue practicing structured answers."]
        study_topics = evaluation.study_recommendations or ["Core Concepts From This Assessment"]
        covered_concepts, missing_concepts = self._concept_lists(evaluation)
        percentage = float(meta["percentage"])

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="GMTitle",
            parent=styles["Title"],
            textColor=gm_dark,
            fontName="Helvetica-Bold",
            fontSize=30,
            leading=34,
            alignment=TA_CENTER,
            spaceAfter=8,
        ))
        styles.add(ParagraphStyle(
            name="GMSubtitle",
            parent=styles["Normal"],
            textColor=gm_blue,
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            alignment=TA_CENTER,
            spaceAfter=18,
        ))
        styles.add(ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            textColor=gm_dark,
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            spaceBefore=12,
            spaceAfter=8,
        ))
        styles.add(ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#344054"),
            fontSize=9.5,
            leading=13,
        ))
        styles.add(ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#667085"),
            fontSize=8,
            leading=10,
        ))
        styles.add(ParagraphStyle(
            name="CardTitle",
            parent=styles["BodyText"],
            textColor=gm_dark,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
        ))

        def text(value: Any) -> str:
            return str(value if value is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def para(value: Any, style_name: str = "Body") -> Paragraph:
            return Paragraph(text(value), styles[style_name])

        def bullet_items(items: List[str], color=gm_dark) -> list:
            return [Paragraph(f'<font color="{color.hexval()}"><b>-</b></font> {text(item)}', styles["Body"]) for item in items]

        def card(title: str, value: str, tint, width=1.8 * inch) -> Table:
            table = Table(
                [[Paragraph(text(title), styles["Small"])], [Paragraph(f"<b>{text(value)}</b>", styles["CardTitle"])]],
                colWidths=[width],
            )
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), tint),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.white),
                ("ROUNDEDCORNERS", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            return table

        def bar_chart() -> Drawing:
            drawing = Drawing(470, 190)
            drawing.add(Rect(0, 0, 470, 190, fillColor=colors.white, strokeColor=colors.HexColor("#E5E7EB")))
            chart_questions = questions[:12]
            if not chart_questions:
                drawing.add(String(175, 90, "No question data available", fillColor=gm_dark, fontSize=11))
                return drawing
            max_marks = max([q.max_marks for q in chart_questions] + [1])
            bar_width = min(28, 360 / max(len(chart_questions), 1))
            gap = 8
            x = 45
            baseline = 35
            chart_height = 115
            drawing.add(String(16, 165, "Question-wise Performance", fillColor=gm_dark, fontSize=12, fontName="Helvetica-Bold"))
            for q in chart_questions:
                height = (q.score_awarded / max_marks) * chart_height if max_marks else 0
                drawing.add(Rect(x, baseline, bar_width, height, fillColor=gm_green, strokeColor=gm_green))
                drawing.add(String(x, baseline - 14, f"Q{q.question_number}", fillColor=colors.HexColor("#667085"), fontSize=7))
                drawing.add(String(x, baseline + height + 5, f"{q.score_awarded:g}", fillColor=gm_dark, fontSize=7))
                x += bar_width + gap
            return drawing

        def doughnut() -> Drawing:
            drawing = Drawing(180, 150)
            drawing.add(Circle(90, 78, 56, fillColor=colors.HexColor("#E5E7EB"), strokeColor=colors.HexColor("#E5E7EB")))
            if percentage >= 99.9:
                drawing.add(Circle(90, 78, 56, fillColor=gm_green, strokeColor=gm_green))
            elif percentage > 0:
                drawing.add(Wedge(90, 78, 56, 90, 90 - (percentage / 100 * 359.9), fillColor=gm_green, strokeColor=gm_green))
            drawing.add(Circle(90, 78, 34, fillColor=colors.white, strokeColor=colors.white))
            drawing.add(String(70, 82, f"{percentage:.0f}%", fillColor=gm_dark, fontSize=18, fontName="Helvetica-Bold"))
            drawing.add(String(61, 64, "Overall Score", fillColor=colors.HexColor("#667085"), fontSize=8))
            return drawing

        def header_footer(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(gm_dark)
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawString(0.55 * inch, page_height - 0.35 * inch, "GradeMIND AI Assessment Report")
            canvas.setFillColor(gm_green)
            canvas.drawRightString(page_width - 0.55 * inch, 0.35 * inch, f"Page {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.55 * inch,
            leftMargin=0.55 * inch,
            topMargin=0.58 * inch,
            bottomMargin=0.55 * inch,
            title="GradeMIND Premium AI Assessment Report",
            author="GradeMIND",
        )

        story = []
        logo_path = self._report_metrics(evaluation).get("logo_path")
        if logo_path and os.path.exists(logo_path):
            story.append(Image(logo_path, width=0.82 * inch, height=0.82 * inch, kind="proportional"))
        story.append(Paragraph("GradeMIND", styles["GMTitle"]))
        story.append(Paragraph("Premium AI Assessment Report", styles["GMSubtitle"]))
        story.append(Spacer(1, 0.12 * inch))
        story.append(Table(
            [[
                Paragraph(f"<b>{text(meta['student_name'])}</b><br/><font color='#667085'>Student</font>", styles["Body"]),
                Paragraph(f"<b>{text(meta['exam_name'])}</b><br/><font color='#667085'>Exam</font>", styles["Body"]),
                Paragraph(f"<b>{text(meta['score_text'])}</b><br/><font color='#667085'>Score</font>", styles["Body"]),
                Paragraph(f"<b>{text(meta['grade'])}</b><br/><font color='#667085'>Grade</font>", styles["Body"]),
            ]],
            colWidths=[1.7 * inch, 1.9 * inch, 1.2 * inch, 1.0 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), gm_light),
                ("BOX", (0, 0), (-1, -1), 1, gm_green),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]),
        ))
        story.append(Spacer(1, 0.24 * inch))
        story.append(Table(
            [[
                card("AI Confidence", f"{meta['confidence_pct']}%", gm_light),
                card("Concept Coverage", f"{meta['coverage_pct']}%", gm_soft_blue),
                card("Fairness Index", f"{meta['fairness_pct']}%", gm_light),
            ]],
            colWidths=[2.0 * inch, 2.0 * inch, 2.0 * inch],
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
        ))

        story.append(Spacer(1, 0.20 * inch))
        story.append(Paragraph("Performance Overview", styles["Section"]))
        story.append(Table([[bar_chart(), doughnut()]], colWidths=[4.7 * inch, 1.9 * inch]))

        story.append(Paragraph("Question Breakdown", styles["Section"]))
        q_rows = [[para("Question", "CardTitle"), para("Marks", "CardTitle"), para("Coverage", "CardTitle"), para("AI Remarks", "CardTitle")]]
        for q in questions:
            coverage = q.concept_coverage if q.concept_coverage is not None else self._question_percentage(q)
            q_rows.append([
                para(f"Q{q.question_number}"),
                para(f"{q.score_awarded:g}/{q.max_marks:g}"),
                para(f"{coverage:.0f}%"),
                para(q.criteria_feedback or "No AI remark available."),
            ])
        question_table = Table(q_rows, colWidths=[0.8 * inch, 0.8 * inch, 0.9 * inch, 3.9 * inch], repeatRows=1)
        question_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), gm_dark),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, gm_light]),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(question_table)

        story.append(PageBreak())
        story.append(Paragraph("Concept Analysis", styles["Section"]))
        story.append(Table(
            [[
                [Paragraph("Covered Concepts", styles["CardTitle"]), *bullet_items(covered_concepts[:10] or ["No covered concepts were detected."], gm_green)],
                [Paragraph("Missing Concepts", styles["CardTitle"]), *bullet_items(missing_concepts[:10] or ["No missing concepts were detected."], gm_red)],
            ]],
            colWidths=[3.1 * inch, 3.1 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), gm_light),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFF1F2")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]),
        ))

        story.append(Paragraph("Strengths vs Weak Areas", styles["Section"]))
        story.append(Table(
            [[
                [Paragraph("Strengths", styles["CardTitle"]), *bullet_items(strengths[:8], gm_green)],
                [Paragraph("Weak Areas", styles["CardTitle"]), *bullet_items(weaknesses[:8], gm_red)],
            ]],
            colWidths=[3.1 * inch, 3.1 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), gm_light),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFF7ED")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]),
        ))

        story.append(Paragraph("Personalized Study Plan", styles["Section"]))
        priority_rows = [[para("High Priority", "CardTitle"), para("Medium Priority", "CardTitle"), para("Low Priority", "CardTitle")]]
        high = missing_concepts[:4] or study_topics[:2]
        medium = study_topics[2:6] or improvements[:4]
        low = study_topics[6:10] or ["Timed practice", "Answer presentation", "Revision notes"]
        priority_rows.append([
            [*bullet_items(high, gm_red)],
            [*bullet_items(medium, gm_blue)],
            [*bullet_items(low, gm_green)],
        ])
        story.append(Table(priority_rows, colWidths=[2.05 * inch, 2.05 * inch, 2.05 * inch], style=TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#FFF1F2")),
            ("BACKGROUND", (1, 0), (1, 0), gm_soft_blue),
            ("BACKGROUND", (2, 0), (2, 0), gm_light),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])))

        story.append(Paragraph("Teacher Insights", styles["Section"]))
        story.append(Table(
            [[para(evaluation.summary or "The submission was evaluated across marks, conceptual coverage, confidence, and feedback quality.")]],
            colWidths=[6.2 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), gm_soft_blue),
                ("BOX", (0, 0), (-1, -1), 0.6, gm_blue),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]),
        ))

        story.append(Paragraph("Detailed AI Feedback", styles["Section"]))
        for q in questions:
            story.append(KeepTogether([
                Table(
                    [[
                        Paragraph(f"<b>Question {text(q.question_number)}</b> <font color='#667085'>({q.score_awarded:g}/{q.max_marks:g})</font>", styles["Body"]),
                    ], [para(q.criteria_feedback or "No detailed feedback available.")]],
                    colWidths=[6.2 * inch],
                    style=TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), gm_light),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]),
                ),
                Spacer(1, 0.08 * inch),
            ]))

        story.append(Paragraph("Final Summary", styles["Section"]))
        story.append(Table(
            [[
                para("Overall Grade", "CardTitle"), para(meta["grade"]),
                para("Top Strength", "CardTitle"), para(strengths[0] if strengths else "Consistent effort"),
            ], [
                para("Improvement Area", "CardTitle"), para(weaknesses[0] if weaknesses else "Advanced practice"),
                para("Recommended Next Topic", "CardTitle"), para(study_topics[0] if study_topics else "Core revision"),
            ]],
            colWidths=[1.25 * inch, 1.85 * inch, 1.45 * inch, 1.65 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), gm_light),
                ("BOX", (0, 0), (-1, -1), 0.8, gm_green),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]),
        ))

        doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
        logger.info("Premium ReportLab PDF fallback generated: output_path=%s", output_path)

    def generate_text_pdf(self, content_lines: List[str], output_path: str) -> None:
        """Generate a compact LaTeX-based PDF for auxiliary documents such as study plans."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        safe_lines = [self._latex_escape(line) for line in content_lines]
        latex_source = "\n".join([
            self._latex_preamble(),
            r"\begin{document}",
            r"\section*{\textcolor{gmdark}{GradeMIND Study Plan}}",
            r"\begin{gmcard}{gmgreen}",
            r"\begin{itemize}",
            "\n".join(rf"\item {line}" for line in safe_lines if line.strip()),
            r"\end{itemize}",
            r"\end{gmcard}",
            r"\end{document}",
        ])
        tex_path = os.path.splitext(output_path)[0] + ".tex"
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_source)
        if self._compile_latex(tex_path, output_path):
            return
        self._write_basic_pdf(content_lines, output_path)

    def _write_basic_pdf(self, content_lines: List[str], output_path: str) -> None:
        """Write a minimal valid PDF only when LaTeX compilation is unavailable."""
        lines_per_page = 58
        pages = [
            content_lines[index:index + lines_per_page]
            for index in range(0, max(len(content_lines), 1), lines_per_page)
        ]
        page_ids = [4 + index * 2 for index in range(len(pages))]
        content_ids = [page_id + 1 for page_id in page_ids]
        objects: List[tuple[int, bytes]] = []

        objects.append((1, b"<< /Type /Catalog /Pages 2 0 R >>"))
        kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
        objects.append((2, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")))
        objects.append((3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>"))

        for page_number, page_lines in enumerate(pages):
            page_id = page_ids[page_number]
            content_id = content_ids[page_number]
            stream_content = "BT\n/F1 10 Tf\n12 TL\n50 800 Td\n"
            for line in page_lines:
                safe_line = (
                    str(line)
                    .replace("\\", "\\\\")
                    .replace("(", "\\(")
                    .replace(")", "\\)")
                )
                stream_content += f"({safe_line[:110]}) Tj T*\n"
            stream_content += "ET\n"
            stream_bytes = stream_content.encode("utf-8", errors="ignore")
            page_obj = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
            )
            content_obj = (
                f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
                + stream_bytes
                + b"endstream"
            )
            objects.append((page_id, page_obj.encode("ascii")))
            objects.append((content_id, content_obj))

        objects.sort(key=lambda item: item[0])
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = {0: 0}
        for object_id, body in objects:
            offsets[object_id] = len(pdf)
            pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
            pdf.extend(body)
            pdf.extend(b"\nendobj\n")

        xref_offset = len(pdf)
        max_object_id = max(object_id for object_id, _ in objects)
        pdf.extend(f"xref\n0 {max_object_id + 1}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for object_id in range(1, max_object_id + 1):
            pdf.extend(f"{offsets.get(object_id, 0):010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            (
                "trailer\n"
                f"<< /Size {max_object_id + 1} /Root 1 0 R >>\n"
                "startxref\n"
                f"{xref_offset}\n"
                "%%EOF\n"
            ).encode("ascii")
        )

        with open(output_path, "wb") as f:
            f.write(pdf)

