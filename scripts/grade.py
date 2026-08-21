"""One command: question paper + answer script + marking scheme -> a report.

    python -m scripts.grade --paper qp.pdf --answers script.pdf \
                            --scheme schemes/x.json --out out/ --mask 0,0,1,0.15 [--offline]

This wires together components that already exist and adds no engine of its
own. The pipeline is:

    rasterize -> mask identity -> transcribe -> segment -> classify
              -> match -> score -> derivation -> annotated PDF -> report.md

WHAT MAKES THIS DIFFERENT FROM `evaluate_script.py`
---------------------------------------------------
It reads the QUESTION PAPER, and cross-checks it against the marking scheme.

That check exists because of a real defect that took a week to find by hand.
`schemes/dl-2026-s1.json` credits CNN, LSTM and the forget gate for question
15. The printed paper asks candidates to "Interpret the impact of attention
mechanisms in improving the performance of image captioning models". The word
"attention" appears nowhere in the scheme. Every mark previously reported for
that question was void, and nothing in the system noticed, because nothing in
the system had ever read the paper.

`check_scheme_against_paper` below is that defect turned into an automatic
check. It runs on every question, on every run, and it would have caught it on
day one.

WHAT IT DOES NOT DO
-------------------
It does not author schemes, and it does not repair them. When the paper and
the scheme disagree it says so in the report and changes nothing. A scheme is
a human artefact and an automated edit to one is an unrecorded change to how
marks are awarded.

It reads the paper's TEXT LAYER only. A scanned or photographed paper has no
text layer, and the report says the check could not run rather than guessing.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from AI.evaluation.scheme_loader import load_marking_scheme
from AI.evaluation.score_computer import compute
from AI.evaluation.value_point import ENGINE_VERSION, SchemeQuestion
from AI.evaluation.value_point_matcher import match
from AI.ocr.content_classifier import ContentClassifier
from AI.ocr.identity_mask import MaskRegion, mask_identity_region
from AI.ocr.providers.cache import FilesystemExtractionCache
from AI.ocr.providers.gemini_vision import GeminiVisionHTRProvider
from AI.ocr.providers.prompts import TRANSCRIPTION_PROMPT_VERSION
from AI.ocr.rasterize import PageImage, rasterize_pdf, sha256_bytes
from AI.ocr.segmentation import segment_script

GRADE_VERSION = "grade-cli/1.0.0"
MATCHER_VERSION = "value-point-matcher/1.0.0"
BANNER = "SUGGESTED MARKS - NOT VALIDATED AGAINST HUMAN EXAMINERS"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

# Flagging threshold for the paper/scheme cross-check.
#
# This number CANNOT CHANGE A MARK. It decides whether a line in the report is
# printed as "FLAG" or "ok", and nothing downstream reads it. The underlying
# evidence -- the exact words in the question that the scheme never mentions,
# and the exact words the scheme credits that the question never asks -- is
# printed for EVERY question regardless of which side of this line it falls,
# so a human is always judging the words rather than trusting the threshold.
#
# It is UNCALIBRATED. No labelled set of mismatched schemes exists to derive it
# from. 0.5 means "fewer than half the question's content words appear anywhere
# in the scheme entry", which is a deliberately loud bar.
SCHEME_OVERLAP_FLOOR = 0.5

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
    "from", "give", "how", "in", "into", "is", "it", "its", "list", "of", "on",
    "one", "or", "the", "their", "them", "there", "these", "they", "this", "to",
    "two", "use", "used", "uses", "using", "was", "what", "when", "where",
    "which", "why", "will", "with", "you", "your", "vs", "versus", "such",
    "following", "any", "also", "between", "about", "above", "over", "under",
}


def _words(text: str) -> List[str]:
    """Content words, lowercased, crudely singularised.

    Singularisation matters: the paper writes "Autoencoders" and a scheme may
    write "autoencoder". Treating those as different words would manufacture a
    mismatch that is not there.
    """
    out = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9\-]*", text.lower()):
        w = raw.strip("-")
        if len(w) < 3 or w in _STOPWORDS:
            continue
        if len(w) > 4 and w.endswith("ies"):
            w = w[:-3] + "y"
        elif len(w) > 3 and w.endswith("es") and not w.endswith("ses"):
            w = w[:-2]
        elif len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


# ---------------------------------------------------------------------------
# The question paper
# ---------------------------------------------------------------------------


@dataclass
class PaperQuestion:
    number: str
    text: str
    part: Optional[str] = None
    part_header: Optional[str] = None
    part_instruction: Optional[str] = None


@dataclass
class Paper:
    questions: Dict[str, PaperQuestion] = field(default_factory=dict)
    read: bool = False
    reason: str = ""
    source: str = ""


_Q_START = re.compile(r"^\s*(\d{1,2})\s*[.)]\s+(\S.*)$")
_PART = re.compile(
    r"^\s*Part\s*[-–]?\s*([A-Z])\s*[-–]\s*\((\d+)\s*[*x×]\s*(\d+)\s*=\s*(\d+)\s*Marks?\)",
    re.IGNORECASE,
)
_INSTRUCTION = re.compile(r"^\s*(Answer\s+(?:any\s+)?\w+\s+questions?.*)$", re.IGNORECASE)


def read_paper(path: Optional[Path]) -> Paper:
    """Parse the paper's text layer. Never OCR, never guess."""
    if path is None:
        return Paper(read=False, reason="no --paper supplied")

    p = Paper(source=str(path))

    if path.suffix.lower() in IMAGE_SUFFIXES:
        p.reason = (
            f"{path.name} is an image. A photographed or scanned paper carries "
            "no text layer, and this command does not OCR the paper. The "
            "paper/scheme cross-check CANNOT RUN on this input."
        )
        return p

    try:
        import pymupdf
        doc = pymupdf.open(path)
        text = "".join(pg.get_text() for pg in doc)
        doc.close()
    except Exception as exc:
        p.reason = f"could not open {path.name}: {exc}"
        return p

    if len(text.strip()) < 50:
        p.reason = (
            f"{path.name} has no usable text layer ({len(text.strip())} chars). "
            "It is probably a scan. The paper/scheme cross-check CANNOT RUN."
        )
        return p

    part = part_header = instruction = None
    cur: Optional[PaperQuestion] = None

    for line in text.splitlines():
        m_part = _PART.match(line)
        if m_part:
            cur = None
            part, part_header = m_part.group(1), line.strip()
            continue
        m_ins = _INSTRUCTION.match(line)
        if m_ins:
            instruction = m_ins.group(1).strip()
            continue
        m_q = _Q_START.match(line)
        if m_q:
            num, rest = m_q.group(1), m_q.group(2)
            cur = PaperQuestion(number=num, text=rest.strip(), part=part,
                                part_header=part_header, part_instruction=instruction)
            # First definition wins: papers repeat question numbers in the
            # mark-allocation tables at the end, and the question body comes
            # first. setdefault keeps the body and ignores the table.
            if num in p.questions:
                cur = p.questions[num]
            else:
                p.questions[num] = cur
            continue
        if cur is not None and line.strip():
            cur.text = (cur.text + " " + line.strip()).strip()

    p.read = bool(p.questions)
    if not p.read:
        p.reason = f"{path.name} has a text layer but no lines matched a question pattern"
    return p


# ---------------------------------------------------------------------------
# The check that would have caught Q14/Q15
# ---------------------------------------------------------------------------


@dataclass
class SchemeCheck:
    question_number: str
    ran: bool
    reason: str = ""
    paper_text: str = ""
    scheme_text: str = ""
    overlap: float = 0.0
    missing_from_scheme: List[str] = field(default_factory=list)
    unasked_by_paper: List[str] = field(default_factory=list)
    marks_note: str = ""
    instruction: str = ""
    flagged: bool = False


def check_scheme_against_paper(sq: SchemeQuestion, paper: Paper) -> SchemeCheck:
    """Does this scheme entry credit what this question actually asks?

    Two directions, because they catch different failures:

      missing_from_scheme  the question asks about something the scheme never
                           mentions. This is how Q15 lost "attention".
      unasked_by_paper     the scheme credits something the question never
                           asks. This is how Q15 gained "forget gate".

    Both lists are printed for every question whether or not the flag fires, so
    the reader judges the words rather than the threshold.
    """
    c = SchemeCheck(question_number=sq.question_number, ran=False)

    if not paper.read:
        c.reason = paper.reason or "paper not read"
        return c

    pq = paper.questions.get(sq.question_number)
    if pq is None:
        c.reason = (
            f"the paper has no question {sq.question_number}, but the scheme "
            "defines one. The scheme may be for a different paper or a "
            "different set."
        )
        c.flagged = True
        c.ran = True
        return c

    c.ran = True
    c.paper_text = pq.text
    c.scheme_text = sq.question_text
    c.instruction = pq.part_instruction or ""

    paper_w = _words(pq.text)
    # The scheme's whole vocabulary: its question text, every value point, and
    # every accepted variant. Being generous here means a flag is meaningful.
    scheme_vocab = set(_words(sq.question_text))
    for vp in sq.value_points:
        scheme_vocab |= set(_words(vp.text))
        for v in vp.acceptable_variants:
            scheme_vocab |= set(_words(v))

    seen, missing = set(), []
    for w in paper_w:
        if w in seen:
            continue
        seen.add(w)
        if w not in scheme_vocab:
            missing.append(w)
    c.missing_from_scheme = missing
    c.overlap = (len(seen) - len(missing)) / len(seen) if seen else 0.0

    paper_vocab = set(paper_w)
    c.unasked_by_paper = sorted({w for w in _words(sq.question_text) if w not in paper_vocab})

    # Mark allocation. The paper writes a part header like "(3*2=6 Marks)" and
    # which factor is "marks" and which is "how many to answer" is not
    # consistent across parts of the same paper, so this asserts only what is
    # safe: the scheme's max_marks should be one of the two factors.
    if pq.part_header:
        m = _PART.match(pq.part_header)
        if m:
            f1, f2, total = int(m.group(2)), int(m.group(3)), int(m.group(4))
            if sq.max_marks in (float(f1), float(f2)):
                c.marks_note = (f"scheme max_marks={sq.max_marks:g} is consistent with the "
                                f"paper's {pq.part_header!r}")
            else:
                c.marks_note = (
                    f"MARK ALLOCATION MISMATCH: scheme max_marks={sq.max_marks:g} "
                    f"is neither factor in the paper's {pq.part_header!r} "
                    f"({f1} or {f2}, total {total})"
                )
                c.flagged = True

    if c.overlap < SCHEME_OVERLAP_FLOOR:
        c.flagged = True
    return c


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------


def load_pages(answers: Path, dpi: int, max_pages: Optional[int]) -> List[PageImage]:
    if answers.suffix.lower() in IMAGE_SUFFIXES:
        from PIL import Image
        with Image.open(answers) as im:
            im = im.convert("RGB")
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            png, (w, h) = buf.getvalue(), im.size
        return [PageImage(page_number=1, image_bytes=png, width=w, height=h, dpi=0,
                          source_sha256=sha256_bytes(answers.read_bytes()),
                          page_sha256=sha256_bytes(png))]
    return rasterize_pdf(answers, dpi=dpi, max_pages=max_pages)


@dataclass
class PageOutcome:
    page_number: int
    ok: bool
    page_sha256: str
    reason: str = ""
    page_confidence: Optional[float] = None
    line_count: int = 0


def transcribe(pages: Sequence[PageImage], region: Optional[MaskRegion],
               offline: bool, cache_root: Path) -> Tuple[List[Any], List[PageOutcome]]:
    """Mask then transcribe. A page that fails is recorded, never faked.

    A failure does not abort the run. It is recorded, reported in COVERAGE, and
    contributes no text, so no question can be scored from a page we could not
    read. That is the failure taxonomy's rule: never a silent zero.
    """
    cache = FilesystemExtractionCache(cache_root)
    provider = GeminiVisionHTRProvider(cache=cache, offline=offline)

    out, outcomes = [], []
    for page in pages:
        masked = mask_identity_region(page, region, require_region=region is not None)
        try:
            tp = provider.extract(masked)
        except Exception as exc:
            outcomes.append(PageOutcome(page.page_number, False, masked.page_sha256,
                                        reason=f"{type(exc).__name__}: {exc}"))
            continue
        out.append(tp)
        outcomes.append(PageOutcome(page.page_number, True, masked.page_sha256,
                                    page_confidence=tp.page_confidence,
                                    line_count=len(tp.lines)))
    return out, outcomes


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _q(text: str, limit: int = 90) -> str:
    t = " ".join(text.split())
    return t if len(t) <= limit else t[: limit - 1] + "..."


def write_report(path: Path, ctx: Dict[str, Any]) -> None:
    L: List[str] = []
    a = L.append

    a(f"# Evaluation report: {ctx['answers_name']}")
    a("")
    a(f"**{BANNER}**")
    a("")
    a("Assist-only. Every mark below is a suggestion with its working shown.")
    a("A human awards the mark.")
    a("")
    a("---")
    a("")
    a("## Summary")
    a("")
    a("| | |")
    a("|---|---|")
    a(f"| Questions scored | {ctx['n_scored']} |")
    a(f"| Questions routed to a human | {ctx['n_routed']} |")
    a(f"| Questions with no scheme entry | {ctx['n_no_scheme']} |")
    a(f"| Marks awarded | {ctx['total_awarded']:g} / {ctx['total_possible']:g} "
      f"(over scored questions only) |")
    a(f"| Scheme entries flagged against the paper | {ctx['n_flagged']} |")
    a("")
    if ctx["n_flagged"]:
        a(f"> **{ctx['n_flagged']} scheme entry(ies) do not match the printed question")
        a("> paper.** Marks for those questions are shown below but are **not")
        a("> defensible** until the scheme is corrected. See the next section.")
        a("")

    a("---")
    a("")
    a("## Scheme against the paper")
    a("")
    a("Does each scheme entry credit what the printed question actually asks?")
    a("The scheme is never modified by this command. Mismatches are reported.")
    a("")
    if not ctx["paper"].read:
        a(f"**NOT RUN.** {ctx['paper'].reason}")
        a("")
        a("Without this check a scheme can credit concepts the paper never asked")
        a("about, and nothing downstream will notice. That has already happened")
        a("once in this project.")
        a("")
    else:
        a(f"Paper text layer read from `{Path(ctx['paper'].source).name}`, "
          f"{len(ctx['paper'].questions)} question(s) parsed.")
        a("")
        for c in ctx["checks"]:
            if not c.ran:
                a(f"### Q{c.question_number} - NOT RUN")
                a("")
                a(c.reason)
                a("")
                continue
            a(f"### Q{c.question_number} - {'**FLAGGED**' if c.flagged else 'ok'}"
              f"  (overlap {c.overlap:.2f})")
            a("")
            if c.paper_text:
                a(f"- **Paper asks:** {_q(c.paper_text, 200)}")
                a(f"- **Scheme says:** {_q(c.scheme_text, 200)}")
            if c.missing_from_scheme:
                a("- **In the question, absent from the entire scheme entry:** "
                  f"`{'`, `'.join(c.missing_from_scheme)}`")
            else:
                a("- Every content word in the question appears somewhere in the scheme entry.")
            if c.unasked_by_paper:
                a("- **Credited by the scheme, never asked by the question:** "
                  f"`{'`, `'.join(c.unasked_by_paper)}`")
            if c.marks_note:
                a(f"- {c.marks_note}")
            if c.instruction:
                a(f"- Paper instruction for this part: *{c.instruction}*")
            if c.reason:
                a(f"- {c.reason}")
            a("")

    a("---")
    a("")
    a("## Marks, with derivations")
    a("")
    for item in ctx["per_question"]:
        qn = item["question_number"]
        if item["kind"] == "routed":
            a(f"### Q{qn} - ROUTED TO A HUMAN")
            a("")
            a(f"Not marked. Reason: `{item['reason']}`")
            a("")
            continue
        if item["kind"] == "no_scheme":
            a(f"### Q{qn} - NOT SCORED - no scheme")
            a("")
            a("The marking scheme has no entry for this question, so nothing was")
            a("awarded and nothing was deducted. **This is not a zero.**")
            a("")
            continue

        s = item["score"]
        flag = "  **[SCHEME FLAGGED - see above]**" if item["flagged"] else ""
        a(f"### Q{qn} - {s.total:g} / {s.max_marks:g}{flag}")
        a("")
        a(f"*{item['question_text']}*")
        a("")
        a("| | Value point | Mark | Evidence |")
        a("|---|---|---|---|")
        for aw in list(s.awarded) + list(s.not_awarded):
            tick = "x" if aw.matched else " "
            if aw.matched and aw.evidence_span:
                st, en = aw.evidence_span
                quoted = " ".join(item["text"][st:en].split())
                ev = f"chars {st}-{en} `{_q(quoted, 70)}`"
            else:
                ev = aw.reason
            a(f"| [{tick}] | {aw.value_point_id} {_q(aw.text, 60)} | "
              f"{aw.awarded:g}/{aw.possible:g} | {ev} |")
        a("")
        if s.uncalibrated:
            a("> At least one match used an UNCALIBRATED threshold. This question")
            a("> cannot be routed to AUTO.")
            a("")

    a("---")
    a("")
    a("## COVERAGE: what this run could not do")
    a("")
    a("Read this section before the marks.")
    a("")
    cov = ctx["coverage"]
    if not cov:
        a("Nothing to report. Every page transcribed, every question had a scheme")
        a("entry, no region was routed, no non-text content was detected.")
        a("")
    for heading, items in cov:
        a(f"**{heading}**")
        a("")
        for i in items:
            a(f"- {i}")
        a("")

    a("---")
    a("")
    a("## Provenance")
    a("")
    a("| field | value |")
    a("|---|---|")
    for k, v in ctx["provenance"].items():
        a(f"| {k} | `{v}` |")
    a("")
    a("**Page hashes** (of the masked bytes, exactly as transcribed):")
    a("")
    a("| page | transcribed | page_sha256 | lines | confidence |")
    a("|---|---|---|---|---|")
    for o in ctx["page_outcomes"]:
        conf = f"{o.page_confidence:.2f}" if o.page_confidence is not None else "-"
        a(f"| {o.page_number} | {'yes' if o.ok else '**NO**'} | `{o.page_sha256[:24]}` | "
          f"{o.line_count if o.ok else '-'} | {conf} |")
    a("")
    a("`confidence` is a model self-reported legibility rating, not a calibrated")
    a("probability. It has never been compared against human transcription.")
    a("")
    a("---")
    a("")
    a(f"**{BANNER}**")
    a("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.grade",
                                 description="Grade one answer script against one marking scheme.")
    ap.add_argument("--paper", type=Path, default=None,
                    help="question paper PDF, read for question text and mark allocation")
    ap.add_argument("--answers", type=Path, required=True, help="answer script PDF or image")
    ap.add_argument("--scheme", type=Path, required=True, help="marking scheme JSON")
    ap.add_argument("--out", type=Path, required=True, help="output directory")
    ap.add_argument("--offline", action="store_true",
                    help="cache only; any cache miss fails loudly and no network call is made")
    ap.add_argument("--mask", type=str, default=None,
                    help="identity region as x0,y0,x1,y1 fractions, e.g. 0,0,1,0.15")
    ap.add_argument("--no-mask", action="store_true",
                    help="explicitly send unmasked pages. Recorded in the report.")
    ap.add_argument("--dpi", type=int, default=150, help="rasterization DPI for a PDF")
    ap.add_argument("--max-pages", type=int, default=None)
    ap.add_argument("--cache", type=Path, default=Path("tmp/htr_cache"))
    ap.add_argument("--expect-questions", type=int, default=15,
                    help="highest question number the segmenter should expect")
    args = ap.parse_args(argv)

    if not args.mask and not args.no_mask:
        print("FATAL: --mask is required (or --no-mask to opt out explicitly).\n"
              "There is deliberately no default identity region: answer-book layouts\n"
              "differ, and a default that fits one exam silently misses the header on\n"
              "another. Verify the region against a real page of THIS exam first.",
              file=sys.stderr)
        return 2

    region = None
    if args.mask:
        try:
            x0, y0, x1, y1 = (float(v) for v in args.mask.split(","))
        except ValueError:
            print(f"FATAL: --mask must be four comma-separated fractions, got {args.mask!r}",
                  file=sys.stderr)
            return 2
        region = MaskRegion(x0, y0, x1, y1, label=f"identity region for {args.answers.name}")

    args.out.mkdir(parents=True, exist_ok=True)

    print(f"{GRADE_VERSION}  offline={args.offline}")
    print(f"  paper   : {args.paper}")
    print(f"  answers : {args.answers}")
    print(f"  scheme  : {args.scheme}")

    scheme_qs = {sq.question_number: sq for sq in load_marking_scheme(args.scheme)}
    print(f"  scheme has {len(scheme_qs)} question(s): "
          f"{', '.join(sorted(scheme_qs, key=lambda s: int(s)))}")

    paper = read_paper(args.paper)
    print("  paper   : " + (f"read, {len(paper.questions)} questions parsed"
                            if paper.read else f"NOT READ ({paper.reason[:70]})"))

    checks = [check_scheme_against_paper(scheme_qs[n], paper)
              for n in sorted(scheme_qs, key=lambda s: int(s))]
    flagged = {c.question_number for c in checks if c.flagged}
    for c in checks:
        if c.flagged:
            print(f"  SCHEME FLAG Q{c.question_number}: overlap={c.overlap:.2f} "
                  f"missing={c.missing_from_scheme}")

    pages = load_pages(args.answers, args.dpi, args.max_pages)
    print(f"  rasterized {len(pages)} page(s)")

    transcribed, outcomes = transcribe(pages, region, args.offline, args.cache)
    print(f"  transcribed {len(transcribed)}/{len(pages)} page(s)")
    for o in outcomes:
        if not o.ok:
            print(f"    page {o.page_number} FAILED: {o.reason[:110]}")

    coverage: List[Tuple[str, List[str]]] = []

    failed = [o for o in outcomes if not o.ok]
    if failed:
        coverage.append((
            f"{len(failed)} page(s) could not be transcribed. Nothing on them was marked.",
            [f"page {o.page_number} (`{o.page_sha256[:16]}`): {o.reason}" for o in failed]))

    if args.max_pages is not None:
        coverage.append((f"Only the first {args.max_pages} page(s) were processed (`--max-pages`).",
                         ["Any content beyond that page was not read and not marked."]))

    if region is None:
        coverage.append(("Identity masking was explicitly disabled (`--no-mask`).",
                         ["Pages were sent to the provider carrying any identifiers they bear."]))

    regions = []
    if transcribed:
        regions = segment_script(
            list(transcribed),
            expected_questions=[str(i) for i in range(1, args.expect_questions + 1)])
    print(f"  segmented {len(regions)} region(s)")

    classifier = ContentClassifier(offline=True)
    per_question: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    n_scored = n_routed = n_no_scheme = 0
    total_awarded = total_possible = 0.0
    routed_notes: List[str] = []
    nonscheme_notes: List[str] = []
    nontext_notes: List[str] = []

    for r in regions:
        flags = classifier.check_transcription_struck_out(r)
        scorable = r.can_be_auto() and not flags.has_flags
        sq = scheme_qs.get(r.question_number)

        base = {"question_number": r.question_number, "page_numbers": r.page_numbers,
                "status": r.status.name, "flags": flags.flagged_reasons(), "lines": r.lines}

        if not scorable:
            n_routed += 1
            reason = (f"CONTAINS_STRUCK_OUT {flags.flagged_reasons()}"
                      if flags.has_flags else f"segmentation status {r.status.name}")
            per_question.append({"kind": "routed", "question_number": r.question_number,
                                 "reason": reason})
            routed_notes.append(f"Q{r.question_number} on page(s) "
                                f"{','.join(map(str, r.page_numbers))}: {reason}")
            if flags.has_flags:
                nontext_notes.append(f"Q{r.question_number}: {flags.flagged_reasons()}")
            results.append({**base, "can_be_auto": False, "score": None})
            continue

        if sq is None:
            n_no_scheme += 1
            per_question.append({"kind": "no_scheme", "question_number": r.question_number})
            nonscheme_notes.append(f"Q{r.question_number}")
            results.append({**base, "can_be_auto": True, "score": None})
            continue

        matches = [match(r.text, vp) for vp in sq.value_points]
        score = compute(matches, sq, r.text)
        n_scored += 1
        total_awarded += score.total
        total_possible += score.max_marks
        per_question.append({"kind": "scored", "question_number": r.question_number,
                             "question_text": sq.question_text, "score": score,
                             "text": r.text, "flagged": r.question_number in flagged})
        results.append({**base, "can_be_auto": True, "score": score.as_dict()})

    if routed_notes:
        coverage.append((f"{len(routed_notes)} region(s) were routed to a human and not marked.",
                         routed_notes))
    if nonscheme_notes:
        coverage.append((
            f"{len(nonscheme_notes)} question(s) have no entry in this marking scheme.",
            [f"{', '.join(nonscheme_notes)} - not scored, and NOT scored as zero.",
             "A mark cannot be awarded or withheld against a criterion that does not exist."]))
    if nontext_notes:
        coverage.append(("Non-text or struck-out content was detected.", nontext_notes))

    low_conf = [o for o in outcomes
                if o.ok and o.page_confidence is not None and o.page_confidence < 0.7]
    if low_conf:
        coverage.append((
            "Pages whose self-reported legibility was low.",
            [f"page {o.page_number}: {o.page_confidence:.2f} (model self-report, uncalibrated)"
             for o in low_conf]))
    if flagged:
        coverage.append((
            f"{len(flagged)} scheme entry(ies) do not match the printed paper.",
            [f"Q{n}: marks shown are NOT defensible until the scheme is corrected."
             for n in sorted(flagged, key=lambda s: int(s))]))
    if not paper.read:
        coverage.append(("The paper/scheme cross-check could not run.", [paper.reason]))

    model_id = transcribed[0].model_id if transcribed else "n/a"
    prompt_version = transcribed[0].prompt_version if transcribed else TRANSCRIPTION_PROMPT_VERSION
    is_image = args.answers.suffix.lower() in IMAGE_SUFFIXES
    provenance = {
        "grade_cli": GRADE_VERSION, "scheme": args.scheme.name,
        "matcher": MATCHER_VERSION, "scorer": ENGINE_VERSION,
        "model_id": model_id, "prompt_version": prompt_version,
        "rasterize_dpi": "n/a (image input)" if is_image else str(args.dpi),
        "identity_mask": args.mask if args.mask else "DISABLED (--no-mask)",
        "offline": str(args.offline),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if not is_image and results:
        try:
            from AI.reports.annotate_pdf import generate_annotated_pdf
            annotated = generate_annotated_pdf(args.answers, args.out / "annotated.pdf",
                                               results, provenance)
            print(f"  annotated PDF -> {annotated}")
        except Exception as exc:
            coverage.append(("The annotated PDF could not be produced.",
                             [f"{type(exc).__name__}: {exc}"]))
            print(f"  annotated PDF FAILED: {exc}")
    else:
        coverage.append(("No annotated PDF was produced.",
                         ["The annotator draws on PDF pages; this input is a single image."]))

    report = args.out / "report.md"
    write_report(report, {
        "answers_name": args.answers.name, "paper": paper, "checks": checks,
        "per_question": per_question, "coverage": coverage, "provenance": provenance,
        "page_outcomes": outcomes, "n_scored": n_scored, "n_routed": n_routed,
        "n_no_scheme": n_no_scheme, "n_flagged": len(flagged),
        "total_awarded": total_awarded, "total_possible": total_possible,
    })

    (args.out / "results.json").write_text(
        json.dumps({"provenance": provenance,
                    "results": [{k: v for k, v in r.items() if k != "lines"} for r in results]},
                   indent=2), encoding="utf-8")

    print(f"\n  {n_scored} scored, {n_routed} routed, {n_no_scheme} no-scheme, "
          f"{len(flagged)} scheme flag(s)")
    print(f"  report -> {report}")
    print(f"  {BANNER}")
    return 0


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=FutureWarning)
    raise SystemExit(main())
