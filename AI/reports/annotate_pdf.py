"""Annotated PDF Generator for GradeMIND.

Overlays evaluation results, question scores, value point ticks/crosses,
translucent evidence span highlights, and teacher routing banners directly onto
the original exam scan PDF using PyMuPDF (fitz).

Includes a cover page summarizing:
  - Total marks awarded / max scorable
  - Scored / routed / no-scheme counts
  - Per-question breakdown table
  - Provenance record & mandatory disclaimer banner:
    "SUGGESTED MARKS - NOT VALIDATED AGAINST HUMAN EXAMINERS"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import fitz

DISCLAIMER = "SUGGESTED MARKS - NOT VALIDATED AGAINST HUMAN EXAMINERS"

# Raster image coordinate space constants (1000px width x 1200px height)
RASTER_WIDTH = 1000.0
RASTER_HEIGHT = 1200.0


def _to_pdf_rect(bbox: Tuple[float, float, float, float], pw: float, ph: float, max_x_margin: float = 495.0) -> fitz.Rect:
    """Converts Line bbox (whether normalized fractions <= 1.0 or 1000x1200 pixels) to PyMuPDF A4 points (595x842)."""
    rx0, ry0, rx1, ry1 = bbox

    # Check if bbox is normalized fractions (<= 1.0) or raster pixels (> 1.0)
    if rx1 <= 1.0 and ry1 <= 1.0:
        nx0, ny0, nx1, ny1 = rx0, ry0, rx1, ry1
    else:
        nx0 = rx0 / RASTER_WIDTH
        ny0 = ry0 / RASTER_HEIGHT
        nx1 = rx1 / RASTER_WIDTH
        ny1 = ry1 / RASTER_HEIGHT

    px0 = nx0 * pw
    py0 = ny0 * ph
    px1 = min(nx1 * pw, max_x_margin)
    py1 = ny1 * ph

    if py1 - py0 < 18.0:
        py1 = py0 + 18.0

    return fitz.Rect(px0, py0, px1, py1)


def generate_annotated_pdf(
    input_pdf_path: str | Path,
    output_pdf_path: str | Path,
    eval_summary: List[Dict[str, Any]],
    provenance: Dict[str, str],
) -> Path:
    in_path = Path(input_pdf_path)
    out_path = Path(output_pdf_path)

    if not in_path.exists():
        raise FileNotFoundError(f"Input scan PDF not found: {in_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(in_path)

    # -------------------------------------------------------------------------
    # 1. Create & Insert Cover Page (Page 0)
    # -------------------------------------------------------------------------
    cover = doc.new_page(0, width=595, height=842)  # Standard A4
    margin_x = 40
    curr_y = 45

    # Title Header
    cover.insert_text((margin_x, curr_y), "GradeMIND — Automated Script Evaluation Report", fontsize=16, color=(0.1, 0.2, 0.5))
    curr_y += 28

    # Disclaimer Banner
    banner_rect = fitz.Rect(margin_x, curr_y, 555, curr_y + 30)
    shape = cover.new_shape()
    shape.draw_rect(banner_rect)
    shape.finish(color=(0.8, 0, 0), fill=(1.0, 0.9, 0.9), fill_opacity=0.9, width=1.5)
    shape.commit()

    cover.insert_text((margin_x + 15, curr_y + 20), DISCLAIMER, fontsize=10, color=(0.7, 0, 0))
    curr_y += 45

    # Compute Overview Metrics
    scored_items = [item for item in eval_summary if item.get("score")]
    routed_items = [item for item in eval_summary if not item.get("can_be_auto")]
    no_scheme_items = [item for item in eval_summary if item.get("can_be_auto") and not item.get("score")]

    total_awarded = sum(item["score"]["total"] for item in scored_items)
    total_possible = sum(item["score"]["max_marks"] for item in scored_items)

    # Total Score Summary Box
    summary_rect = fitz.Rect(margin_x, curr_y, 555, curr_y + 45)
    shape = cover.new_shape()
    shape.draw_rect(summary_rect)
    shape.finish(color=(0, 0.4, 0.8), fill=(0.93, 0.96, 1.0), fill_opacity=0.9, width=1.0)
    shape.commit()

    cover.insert_text((margin_x + 15, curr_y + 20), f"TOTAL SCORED: {total_awarded:g} / {total_possible:g} marks", fontsize=12, color=(0, 0.3, 0.7))
    cover.insert_text((margin_x + 240, curr_y + 20), f"Breakdown: {len(scored_items)} scored, {len(routed_items)} routed to human, {len(no_scheme_items)} no-scheme", fontsize=10, color=(0.2, 0.2, 0.2))
    curr_y += 60

    # Summary Table Header
    cover.insert_text((margin_x, curr_y), "Per-Question Breakdown Table", fontsize=12, color=(0.1, 0.1, 0.1))
    curr_y += 18

    # Table Header Line
    cover.insert_text((margin_x, curr_y), "Q#    Pages   Status                   Flags / Routing                  Marks Awarded", fontsize=9, color=(0.3, 0.3, 0.3))
    curr_y += 6
    cover.draw_line((margin_x, curr_y), (555, curr_y), color=(0.7, 0.7, 0.7), width=0.8)
    curr_y += 14

    for item in eval_summary:
        q_num = item["question_number"]
        pages_str = "[" + ",".join(str(p) for p in item["page_numbers"]) + "]"
        status_str = item["status"]
        flags = item.get("flags", ())

        if not item.get("can_be_auto"):
            flag_str = f"ROUTED: {flags[0] if flags else 'MANDATORY_HUMAN'}"
            marks_str = "N/A (Teacher)"
        elif item.get("score"):
            sc = item["score"]
            flag_str = "None (Clean Prose)"
            marks_str = f"{sc['total']:g} / {sc['max_marks']:g}"
        else:
            flag_str = "None (Clean Prose)"
            marks_str = "NO SCHEME"

        row_txt = f"Q{q_num:<4} {pages_str:<7} {status_str:<24} {flag_str:<32} {marks_str}"
        cover.insert_text((margin_x, curr_y), row_txt, fontsize=8.5, color=(0, 0, 0))
        curr_y += 13

        if curr_y > 700:
            break

    curr_y += 15
    # Provenance Block
    cover.insert_text((margin_x, curr_y), "Provenance Metadata Record", fontsize=11, color=(0.1, 0.1, 0.1))
    curr_y += 14

    prov_box = fitz.Rect(margin_x, curr_y, 555, curr_y + 70)
    shape = cover.new_shape()
    shape.draw_rect(prov_box)
    shape.finish(color=(0.6, 0.6, 0.6), fill=(0.97, 0.97, 0.97), fill_opacity=0.9, width=0.8)
    shape.commit()

    p_y = curr_y + 16
    for k, v in provenance.items():
        cover.insert_text((margin_x + 15, p_y), f"{k:<18}: {v}", fontsize=8.5, color=(0.2, 0.2, 0.2))
        p_y += 12

    # -------------------------------------------------------------------------
    # 2. Annotate Original Pages (Indices 1..N)
    # -------------------------------------------------------------------------
    margin_right_x = 510.0  # Right margin text zone (510pt - 585pt) outside handwriting
    max_highlight_x = 495.0  # Maximum right boundary for translucent highlight rects

    for item in eval_summary:
        q_num = item["question_number"]
        page_nums = item["page_numbers"]
        score_info = item.get("score")
        can_auto = item.get("can_be_auto")
        flags = item.get("flags", ())
        lines = item.get("lines", ())

        # Compute character offsets for lines in question region
        line_offsets = []
        offset = 0
        for l in lines:
            start_char = offset
            end_char = offset + len(l.text)
            line_offsets.append((start_char, end_char, l))
            offset = end_char + 1  # space joined

        for p_num in page_nums:
            pdf_page_idx = p_num  # page_num 1 maps to index 1 (shifted +1 by cover)
            if pdf_page_idx >= len(doc):
                continue

            page = doc[pdf_page_idx]
            pw = page.rect.width
            ph = page.rect.height

            # A. Draw Struck-Through Banner for Q10 directly beside Q10's line
            if not can_auto and "CONTAINS_STRUCK_OUT" in flags:
                q10_line = None
                for l in lines:
                    if getattr(l, "struck_through", False) or "10." in l.text:
                        q10_line = l
                        break

                if q10_line and getattr(q10_line, "bbox", None):
                    q10_rect = _to_pdf_rect(q10_line.bbox, pw, ph, max_highlight_x)
                    b_rect = fitz.Rect(140, q10_rect.y0 - 2, 500, q10_rect.y1 + 2)
                    b_shape = page.new_shape()
                    b_shape.draw_rect(b_rect)
                    b_shape.finish(color=(0.8, 0, 0), fill=(1.0, 0.9, 0.9), fill_opacity=0.9, width=1.2)
                    b_shape.commit()
                    page.insert_text((150, q10_rect.y0 + 13), "SENT TO TEACHER — answer struck through", fontsize=10, color=(0.8, 0, 0))

            # B. Draw Scored Question Marks & Evidence Spans
            if score_info:
                # Find top Y of question region for question score display
                first_line = lines[0] if lines else None
                q_top_y = (_to_pdf_rect(first_line.bbox, pw, ph, max_highlight_x).y0) if (first_line and getattr(first_line, "bbox", None)) else 100.0

                # Question Total Score in Right Margin
                page.insert_text((margin_right_x, q_top_y + 12), f"Q{q_num}: {score_info['total']:g}/{score_info['max_marks']:g}", fontsize=11, color=(0.8, 0, 0))

                # Value Points Ticks/Crosses & Evidence Span Highlights
                awarded_lines = score_info.get("awarded", [])
                not_awarded_lines = score_info.get("not_awarded", [])

                # Track vertical offset in margin for ticks/crosses so they never collide
                margin_y = q_top_y + 26

                # Process awarded lines (translucent highlight + green tick)
                for award in awarded_lines:
                    vp_id = award["value_point_id"]
                    span = award.get("evidence_span")

                    if span:
                        span_start, span_end = span[0], span[1]
                        matched_lines = [l for s, e, l in line_offsets if not (e <= span_start or s >= span_end)]

                        if not matched_lines and lines:
                            matched_lines = [lines[0]]

                        # Highlight every line overlapping evidence span
                        first_hl_rect = None
                        for m_line in matched_lines:
                            if getattr(m_line, "bbox", None):
                                hl_rect = _to_pdf_rect(m_line.bbox, pw, ph, max_highlight_x)
                                if first_hl_rect is None:
                                    first_hl_rect = hl_rect

                                h_shape = page.new_shape()
                                h_shape.draw_rect(hl_rect)
                                h_shape.finish(color=(0, 0.7, 0), fill=(1.0, 0.95, 0.4), fill_opacity=0.35, width=1.0)
                                h_shape.commit()

                        tick_y = first_hl_rect.y0 + 12 if first_hl_rect else margin_y
                        page.insert_text((margin_right_x, tick_y), f"[+] {vp_id}", fontsize=9, color=(0, 0.6, 0))
                        margin_y = max(margin_y + 14, tick_y + 14)
                    else:
                        page.insert_text((margin_right_x, margin_y), f"[+] {vp_id}", fontsize=9, color=(0, 0.6, 0))
                        margin_y += 14

                # Process not awarded lines (red cross in margin)
                for award in not_awarded_lines:
                    vp_id = award["value_point_id"]
                    page.insert_text((margin_right_x, margin_y), f"[X] {vp_id}", fontsize=9, color=(0.8, 0, 0))
                    margin_y += 14

    # Save output PDF
    doc.save(out_path)
    doc.close()
    return out_path
