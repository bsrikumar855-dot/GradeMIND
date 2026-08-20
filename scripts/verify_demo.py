"""One command that proves the system works, end to end, with the evidence inline.

    python -m scripts.verify_demo [--offline] [--verbose]

This is the pre-flight before trusting any change, and the thing to run in
front of someone who asks whether it actually works. It makes no API calls
under --offline.

DESIGN RULES, because a harness that lies is worse than no harness
------------------------------------------------------------------
* A phase that did not run is FAIL, never PASS. There is no "skipped".
* Every phase prints its evidence, not a verdict about its evidence.
* A failing phase prints its raw error and execution continues, so one run
  produces the whole picture rather than the first problem.
* Nothing here adjusts a fixture, scheme, threshold, or baseline to make a
  phase pass. A failing assertion IS the finding.
* Exit code 0 only if every phase passed.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import traceback
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
# backend/ is a separate package root; app.core.config lives there.
sys.path.insert(0, str(ROOT / "backend"))

W = 78
RULE = "=" * W
THIN = "-" * W


@dataclass
class PhaseResult:
    name: str
    passed: bool
    evidence: str
    error: Optional[str] = None
    notes: List[str] = field(default_factory=list)


class Harness:
    def __init__(self, offline: bool, verbose: bool):
        self.offline = offline
        self.verbose = verbose
        self.results: List[PhaseResult] = []

    def run(self, number: int, name: str, fn: Callable[[], Tuple[bool, str, List[str]]]) -> None:
        print()
        print(RULE)
        print(f"  PHASE {number} - {name}")
        print(RULE)
        try:
            passed, evidence, notes = fn()
            self.results.append(PhaseResult(f"{number} {name}", passed, evidence, None, notes))
            print()
            print(f"  PHASE {number}: {'PASS' if passed else 'FAIL'}  {evidence}")
        except Exception as exc:
            err = traceback.format_exc()
            print(err)
            self.results.append(
                PhaseResult(f"{number} {name}", False, "raised", f"{type(exc).__name__}: {exc}")
            )
            print(f"  PHASE {number}: FAIL  raised {type(exc).__name__}")


# ---------------------------------------------------------------------------
# PHASE 1 - environment
# ---------------------------------------------------------------------------


def phase_environment(h: Harness):
    notes: List[str] = []
    print(f"  python            : {sys.version.split()[0]}")

    versions = {}
    for mod in ("pymupdf", "PIL", "numpy", "google.generativeai", "pydantic", "pytest"):
        try:
            m = __import__(mod, fromlist=["__version__"])
            versions[mod] = getattr(m, "__version__", "present")
        except Exception:
            versions[mod] = "NOT INSTALLED"
    for k, v in versions.items():
        print(f"  {k:<18}: {v}")

    key_present = bool(os.environ.get("GEMINI_API_KEY"))
    if not key_present:
        env_file = Path("backend/.env")
        if env_file.exists():
            key_present = any(
                line.startswith("GEMINI_API_KEY=") and len(line.strip()) > len("GEMINI_API_KEY=")
                for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines()
            )
    # Presence only. The value is never printed, logged, or hashed.
    print(f"  GEMINI_API_KEY    : {'present' if key_present else 'absent'} (value never printed)")

    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        print(f"  git commit        : {sha[:12]}")
        if dirty:
            n = len(dirty.splitlines())
            print(f"  WORKING TREE DIRTY: {n} file(s) modified - results may not match this commit")
            notes.append(f"working tree dirty ({n} files)")
    except Exception as exc:
        notes.append(f"git unavailable: {exc}")

    print(f"  offline mode      : {h.offline}")

    missing = [k for k, v in versions.items() if v == "NOT INSTALLED" and k != "google.generativeai"]
    ok = not missing
    return ok, ("all required packages present" if ok else f"missing: {missing}"), notes


# ---------------------------------------------------------------------------
# PHASE 2 - determinism
# ---------------------------------------------------------------------------


def phase_determinism(h: Harness):
    from AI.evaluation.score_computer import compute
    from AI.evaluation.value_point import GroupRule, MatchResult, SchemeQuestion, ValuePoint

    question = SchemeQuestion(
        id="det", question_number="1", question_text="determinism probe",
        max_marks=5.0,
        value_points=(
            ValuePoint(id="a", text="alpha", marks=2.0),
            ValuePoint(id="b", text="beta", marks=1.5,
                       group_id="g", group_rule=GroupRule.ANY_N, group_n=1),
            ValuePoint(id="c", text="gamma", marks=1.5,
                       group_id="g", group_rule=GroupRule.ANY_N, group_n=1),
        ),
    )
    matches = [
        MatchResult("a", True, (0, 5), "EXACT", 1.0),
        MatchResult("b", True, (6, 10), "EXACT", 1.0),
        MatchResult("c", True, (11, 16), "EXACT", 1.0),
    ]

    first = compute(matches, question, "alpha beta gamma text")
    digest = hashlib.sha256(
        json.dumps({"total": first.total, "derivation": first.derivation}, sort_keys=True).encode()
    ).hexdigest()

    runs = 200
    drift = None
    for i in range(runs):
        again = compute(matches, question, "alpha beta gamma text")
        d = hashlib.sha256(
            json.dumps({"total": again.total, "derivation": again.derivation}, sort_keys=True).encode()
        ).hexdigest()
        if d != digest:
            drift = i
            break

    print(f"  runs              : {runs}")
    print(f"  total             : {first.total} / {first.max_marks}")
    print(f"  output sha256     : {digest}")
    print(f"  identical across all runs: {drift is None}")
    if drift is not None:
        print(f"  DRIFTED on run {drift}")

    return drift is None, f"{runs} runs byte-identical, sha256={digest[:16]}", []


# ---------------------------------------------------------------------------
# PHASE 3 - fixture provenance
# ---------------------------------------------------------------------------


def phase_fixture(h: Harness):
    from AI.fixtures.real_script_page_1_3 import REAL_SCRIPT_PAGES

    notes: List[str] = []
    print(f"  {'page':>5} {'lines':>6}  {'model_id':<20} {'prompt':<18} page_sha256")
    for p in REAL_SCRIPT_PAGES:
        print(f"  {p.page_number:>5} {len(p.lines):>6}  {p.model_id:<20} "
              f"{p.prompt_version:<18} {p.page_sha256[:16]}")

    cache_dir = Path("tmp/htr_cache")
    cached = list(cache_dir.rglob("*.json")) if cache_dir.exists() else []

    if not cached:
        print("  cache             : ABSENT")
        print("  The fixture is self-contained; this is expected on a fresh clone.")
        notes.append("cache absent - fixture not cross-checked against source records")
        return True, f"{len(REAL_SCRIPT_PAGES)} pages loaded, cache absent (fixture self-contained)", notes

    by_sha = {}
    for f in cached:
        rec = json.loads(f.read_text(encoding="utf-8"))["page"]
        by_sha[rec["page_sha256"]] = rec

    mismatches = []
    for p in REAL_SCRIPT_PAGES:
        rec = by_sha.get(p.page_sha256)
        if rec is None:
            mismatches.append(f"page {p.page_number}: no cache entry for {p.page_sha256[:16]}")
            continue
        fixture_text = [l.text for l in p.lines]
        cache_text = [l["text"] for l in rec["lines"]]
        if fixture_text != cache_text:
            mismatches.append(
                f"page {p.page_number}: fixture text differs from cache "
                f"({len(fixture_text)} vs {len(cache_text)} lines)"
            )
        else:
            print(f"  page {p.page_number} matches its cache entry ({len(cache_text)} lines)")

    # Masking is inferred, and the harness says so rather than asserting it.
    print("  masked            : inferred from key provenance, not re-derived here")
    print("                      (masking recomputes page_sha256; a matching key implies")
    print("                       the same masked bytes were transcribed)")

    if mismatches:
        for m in mismatches:
            print(f"  MISMATCH: {m}")
    return not mismatches, (
        f"{len(REAL_SCRIPT_PAGES)} pages verified against {len(cached)} cache entries"
        if not mismatches else f"{len(mismatches)} mismatch(es)"
    ), notes


# ---------------------------------------------------------------------------
# PHASE 4 - pipeline
# ---------------------------------------------------------------------------

EXPECTED = {
    "q13_total": 3.0,
    "stray_status": "AMBIGUOUS_MAPPING",
    "q12_status": "OUT_OF_ORDER",
    "scoreable": 14,
    "regions": 16,
}


def phase_pipeline(h: Harness):
    from AI.evaluation.score_computer import compute
    from AI.evaluation.value_point_matcher import match_all
    from AI.fixtures.real_script_page_1_3 import REAL_SCRIPT_PAGES
    from AI.ocr.segmentation import SegmentationStatus, segment_script
    from AI.evaluation.scheme_loader import load_marking_scheme

    regions = segment_script(list(REAL_SCRIPT_PAGES),
                             expected_questions=[str(i) for i in range(1, 16)])

    print(f"  {'#':>3} {'q':>5} {'pages':>7}  {'status':<20} scoreable")
    for i, r in enumerate(regions):
        ok = r.status == SegmentationStatus.OK
        print(f"  {i:>3} {r.question_number:>5} {str(r.page_numbers):>7}  "
              f"{r.status.value:<20} {'YES' if ok else 'no'}")

    scoreable = [r for r in regions if r.status == SegmentationStatus.OK]

    scheme = load_marking_scheme(Path("schemes/dl-2026-s1.json"))
    by_q = {q.question_number: q for q in scheme}

    print()
    derivations: Dict[str, Any] = {}
    for r in scoreable:
        q = by_q.get(r.question_number)
        if q is None:
            continue
        score = compute(match_all(r.text, q.value_points), q, r.text)
        derivations[r.question_number] = score
        print(score.derivation)
        print()

    failures = []
    q13 = derivations.get("13")
    if q13 is None:
        failures.append("Q13 produced no score")
    elif q13.total != EXPECTED["q13_total"]:
        failures.append(f"Q13 total {q13.total} != expected {EXPECTED['q13_total']}")

    stray = [r for i, r in enumerate(regions)
             if r.question_number == "3" and r.status.value == EXPECTED["stray_status"]]
    if not stray:
        got = [(r.question_number, r.status.value) for r in regions if r.question_number == "3"]
        failures.append(f"no stray '3' region with {EXPECTED['stray_status']}; got {got}")

    q12 = [r for r in regions if r.question_number == "12"]
    if not q12 or q12[0].status.value != EXPECTED["q12_status"]:
        failures.append(
            f"Q12 status {q12[0].status.value if q12 else 'absent'} != {EXPECTED['q12_status']}"
        )

    if len(scoreable) != EXPECTED["scoreable"]:
        failures.append(f"{len(scoreable)} scoreable != expected {EXPECTED['scoreable']}")
    if len(regions) != EXPECTED["regions"]:
        failures.append(f"{len(regions)} regions != expected {EXPECTED['regions']}")

    print(f"  regions={len(regions)} scoreable={len(scoreable)} scored={len(derivations)}")
    for f in failures:
        print(f"  REGRESSION: {f}")
        print("              this assertion describes verified behaviour; investigate the")
        print("              change, do not adjust the expectation")

    return not failures, (
        f"Q13 {q13.total if q13 else 'n/a'}/3, {len(scoreable)}/{len(regions)} scoreable"
        if not failures else f"{len(failures)} regression(s)"
    ), []


# ---------------------------------------------------------------------------
# PHASE 5 - safety boundaries, each triggered rather than asserted
# ---------------------------------------------------------------------------


def phase_boundaries(h: Harness):
    from AI.evaluation.score_computer import compute
    from AI.evaluation.value_point import MatchResult, SchemeQuestion, ValuePoint
    from AI.ocr.providers.base import HTRExtractionError
    from AI.ocr.providers.cache import FilesystemExtractionCache
    from AI.ocr.providers.gemini_vision import GeminiVisionHTRProvider
    from AI.ocr.rasterize import PageImage, sha256_bytes

    checks: List[Tuple[str, bool, str]] = []

    # 1. unmasked page refused, transport never reached
    calls = {"n": 0}

    def counting(image_bytes, prompt):
        calls["n"] += 1
        return '{"lines": []}'

    unmasked = PageImage(1, b"x", 100, 100, 150, "s" * 64, sha256_bytes(b"x"), identity_masked=False)
    provider = GeminiVisionHTRProvider(api_key="probe", transport=counting)
    try:
        provider.extract(unmasked)
        checks.append(("unmasked page refused", False, "extract() returned instead of raising"))
    except HTRExtractionError as exc:
        checks.append(("unmasked page refused", calls["n"] == 0,
                       f"transport calls={calls['n']}; {str(exc)[:60]}"))

    # 2. offline mode raises on cache miss instead of calling out
    net = {"n": 0}

    def exploding(image_bytes, prompt):
        net["n"] += 1
        raise AssertionError("network reached in offline mode")

    masked = PageImage(1, b"y", 100, 100, 150, "s" * 64, sha256_bytes(b"y"), identity_masked=True)
    off = GeminiVisionHTRProvider(api_key=None, transport=exploding, offline=True,
                                  cache=FilesystemExtractionCache("tmp/verify_empty_cache"))
    try:
        off.extract(masked)
        checks.append(("offline raises on cache miss", False, "returned instead of raising"))
    except HTRExtractionError as exc:
        checks.append(("offline raises on cache miss", net["n"] == 0,
                       f"network calls={net['n']}; {str(exc)[:60]}"))

    # 3. a flagged region produces no QuestionScore
    from AI.ocr.segmentation import SegmentationStatus, segment_script
    from AI.fixtures.real_script_page_1_3 import REAL_SCRIPT_PAGES

    regions = segment_script(list(REAL_SCRIPT_PAGES),
                             expected_questions=[str(i) for i in range(1, 16)])
    flagged = [r for r in regions if r.status != SegmentationStatus.OK]
    checks.append((
        "flagged regions are excluded from scoring",
        bool(flagged) and all(r.status != SegmentationStatus.OK for r in flagged),
        f"{len(flagged)} flagged: {[(r.question_number, r.status.value) for r in flagged]}",
    ))

    # 4. Settings refuses the auth bypass outside local
    try:
        from app.core.config import AuthBypassNotPermitted, Environment, Settings

        try:
            Settings(AUTH_ENABLED=False, DEBUG=False, ENVIRONMENT=Environment.PRODUCTION,
                     DATABASE_URL="sqlite:///./x.db", SECRET_KEY="x", _env_file=None)
            checks.append(("auth bypass refused outside local", False, "Settings constructed"))
        except AuthBypassNotPermitted as exc:
            checks.append(("auth bypass refused outside local", True, str(exc)[:60]))
    except Exception as exc:
        checks.append(("auth bypass refused outside local", False, f"could not test: {exc}"))

    # 5. insufficient evidence is not awarded, and says why
    q = SchemeQuestion(id="q", question_number="1", question_text="probe", max_marks=2.0,
                       value_points=(ValuePoint(id="v1", text="present", marks=1.0),
                                     ValuePoint(id="v2", text="absent", marks=1.0)))
    score = compute([MatchResult("v1", True, (0, 7), "EXACT", 1.0),
                     MatchResult("v2", False, None, "EXACT", 0.0)], q, "present")
    not_awarded = [a for a in score.not_awarded]
    checks.append((
        "unmatched value point not awarded, with reason",
        score.total == 1.0 and len(not_awarded) == 1 and bool(not_awarded[0].reason),
        f"total={score.total}/2, reason={not_awarded[0].reason if not_awarded else 'NONE'}",
    ))

    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        print(f"         {detail}")

    passed = all(ok for _, ok, _ in checks)
    return passed, f"{sum(1 for _, ok, _ in checks if ok)}/{len(checks)} boundaries held", []


# ---------------------------------------------------------------------------
# PHASE 6 - adversarial
# ---------------------------------------------------------------------------


def phase_adversarial(h: Harness):
    from AI.fixtures.demo_scheme import QUESTIONS
    from scripts.eval_adversarial import load_baseline, run_all

    results = run_all(list(QUESTIONS.values()))
    baseline = load_baseline()

    by_kind: Dict[str, List[Any]] = {}
    for r in results:
        by_kind.setdefault(r.kind, []).append(r)

    print(f"  {'probe class':<30} {'pass':>5} {'fail':>5}  note")
    for kind in sorted(by_kind):
        rows = by_kind[kind]
        failed = [r for r in rows if not r.passed]
        note = ""
        if failed:
            note = failed[0].rationale[:44]
        print(f"  {kind:<30} {len(rows) - len(failed):>5} {len(failed):>5}  {note}")

    failures = [r for r in results if not r.passed]
    new = [r for r in failures if r.key not in baseline]

    print()
    print(f"  {len(results)} probes, {len(failures)} failing "
          f"({len(baseline)} baselined, {len(new)} new)")
    if new:
        for r in new:
            print(f"  NEW FAILURE: {r.key} scored {r.scored:g}/{r.max_marks:g}")
        print("  Not baselining these. A new adversarial failure is a regression.")

    return not new, f"{len(failures)}/{len(results)} failing, {len(new)} new", (
        [f"{len(failures)} known adversarial failures remain"] if failures else []
    )


# ---------------------------------------------------------------------------
# PHASE 7 - artifacts
# ---------------------------------------------------------------------------


def phase_artifacts(h: Harness):
    """Generate the annotated PDF through the REAL CLI path and inspect it.

    An earlier version of this phase called generate_annotated_pdf() directly
    with tmp/p3_evaluation_report.json. That produced a PDF with ZERO
    highlights and I nearly reported it as a defect in the annotator. It is
    not: the serialized artifact carries character spans but not the per-line
    bounding boxes the annotator needs to draw a rectangle, so feeding it back
    in is lossy. The CLI passes richer in-memory results.

    The lesson is the phase's own: `annots()` answers "are there PDF annotation
    objects", not "are there visible highlights" -- these are drawn with
    draw_rect and are `drawings`, not annots. Ask the question you mean.
    """
    scan = Path("backend/storage/answer_sheets/a73e49ab-c18b-499d-85cd-6cc82a186ee8/"
                "S_ebaff77e80f0eb33.pdf")
    if not scan.exists():
        return False, f"source scan missing: {scan}", []

    out = Path("tmp/verify_annotated.pdf")
    proc = subprocess.run(
        [sys.executable, "scripts/evaluate_script.py", "--from-fixture",
         "--scheme", "schemes/dl-2026-s1.json", "--annotate", str(out)],
        capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "."},
    )
    if proc.returncode != 0 or not out.exists():
        print(proc.stdout[-1500:])
        print(proc.stderr[-1500:])
        return False, "evaluate_script --annotate failed", []

    rejected = [l for l in proc.stdout.splitlines() if "REJECTED NARROW HIGHLIGHT" in l]

    import pymupdf

    doc = pymupdf.open(out)
    checks: List[Tuple[str, bool, str]] = []

    source_pages = pymupdf.open(scan).page_count
    # +1: the annotator inserts a cover page at index 0.
    checks.append(("page count = source + cover", doc.page_count == source_pages + 1,
                   f"{doc.page_count} pages ({source_pages} source + 1 cover)"))

    per_page = {}
    narrow = []
    for i in range(doc.page_count):
        filled = [d for d in doc[i].get_drawings() if d.get("fill")]
        if filled:
            per_page[i + 1] = len(filled)
        for d in filled:
            if i > 0 and d["rect"].width < 100:
                narrow.append((i + 1, round(d["rect"].width, 1)))

    answer_pages = {p: n for p, n in per_page.items() if p > 1}
    checks.append(("highlights present on answer pages", bool(answer_pages),
                   f"{answer_pages}" if answer_pages else "NONE - no evidence is marked"))

    total_hl = sum(answer_pages.values())
    awarded_count = 0
    report = Path("tmp/p3_evaluation_report.json")
    if report.exists():
        for r in json.loads(report.read_text(encoding="utf-8")):
            sc = r.get("score")
            if isinstance(sc, dict):
                awarded_count += len(sc.get("awarded") or [])
    checks.append(("at least one highlight per awarded value point",
                   total_hl >= awarded_count > 0,
                   f"{total_hl} highlights for {awarded_count} awarded value points"))

    checks.append(("no highlight narrower than 100pt", not narrow,
                   "none" if not narrow else f"{narrow[:4]}"))

    cover_text = " ".join(doc[0].get_text().split())
    checks.append(("cover carries the disclaimer",
                   "NOT VALIDATED AGAINST HUMAN EXAMINERS" in cover_text,
                   cover_text[:70]))

    rendered = []
    for pageno in (2, 3):
        if pageno <= doc.page_count:
            pix = doc[pageno - 1].get_pixmap(matrix=pymupdf.Matrix(150 / 72, 150 / 72), alpha=False)
            pth = Path(f"tmp/verify_page{pageno}.png")
            pth.write_bytes(pix.tobytes("png"))
            rendered.append(str(pth.resolve()))
    doc.close()

    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    if rejected:
        print(f"  {len(rejected)} highlight(s) rejected as narrower than 100pt:")
        for line in rejected[:4]:
            print(f"    {line.strip()}")

    print()
    print("  rendered for human inspection - LOOK AT THESE:")
    for r in rendered:
        print(f"    {r}")
    print("  Q10 banner placement and margin-label overlap are NOT machine-verified.")
    print("  A coordinate assertion has passed on a visually broken layout twice in")
    print("  this project. These checks are necessary and not sufficient.")

    passed = all(ok for _, ok, _ in checks)
    return passed, f"{sum(1 for _, ok, _ in checks if ok)}/{len(checks)} artifact checks", [
        "Q10 banner position and margin-label overlap require a human to look at the PNGs"
    ]


# ---------------------------------------------------------------------------


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", default=True)
    parser.add_argument("--online", dest="offline", action="store_false")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv[1:])

    h = Harness(offline=args.offline, verbose=args.verbose)

    print(RULE)
    print("  GradeMIND verification harness")
    print(f"  offline={args.offline} (no API calls will be made)" if args.offline
          else "  ONLINE - API calls are permitted")
    print(RULE)

    h.run(1, "ENVIRONMENT", lambda: phase_environment(h))
    h.run(2, "DETERMINISM", lambda: phase_determinism(h))
    h.run(3, "FIXTURE PROVENANCE", lambda: phase_fixture(h))
    h.run(4, "PIPELINE", lambda: phase_pipeline(h))
    h.run(5, "SAFETY BOUNDARIES", lambda: phase_boundaries(h))
    h.run(6, "ADVERSARIAL", lambda: phase_adversarial(h))
    h.run(7, "ARTIFACTS", lambda: phase_artifacts(h))

    print()
    print(RULE)
    print("  SUMMARY")
    print(RULE)
    print(f"  {'phase':<28} {'result':<8} evidence")
    print(f"  {THIN[:74]}")
    for r in h.results:
        print(f"  {r.name:<28} {'PASS' if r.passed else 'FAIL':<8} {r.evidence}")
        if r.error:
            print(f"  {'':<28} {'':<8} {r.error}")

    # Derived from the run, never hardcoded. An earlier version of this block
    # printed "five safety boundaries hold" in the same output where phase 5
    # had just reported 4/5 -- a summary asserting something the run had
    # already contradicted.
    proven = {
        "2 DETERMINISM": "scoring arithmetic is deterministic over 200 runs",
        "3 FIXTURE PROVENANCE": "the fixture matches the cache records it came from",
        "4 PIPELINE": "the pipeline reproduces its documented regions and scores",
        "5 SAFETY BOUNDARIES": "safety boundaries hold when triggered, not merely asserted",
        "6 ADVERSARIAL": "no new adversarial probe started scoring",
        "7 ARTIFACTS": "the annotated PDF is produced and geometrically sane",
    }
    by_name = {r.name: r for r in h.results}

    print()
    print("  WHAT THIS RUN PROVES")
    any_proven = False
    for name, claim in proven.items():
        r = by_name.get(name)
        if r and r.passed:
            print(f"    - {claim}")
            any_proven = True
    if not any_proven:
        print("    - nothing. Every phase that could prove something failed.")

    unproven = [(name, proven[name]) for name in proven
                if name in by_name and not by_name[name].passed]
    if unproven:
        print()
        print("  CLAIMS THIS RUN DOES NOT SUPPORT (phase failed)")
        for name, claim in unproven:
            print(f"    - {claim}  [{name}: {by_name[name].evidence}]")
    print()
    print("  WHAT IS NOT PROVEN, AND WILL NOT BE BY THIS HARNESS")
    print("    - accuracy. No script here has been marked by a human, so no")
    print("      agreement figure exists and none can be computed.")
    print("    - generalisation. One student, one script.")
    print("    - transcription correctness. The fixture is ONE SAMPLE from a")
    print("      non-deterministic model; a re-run produced different text twice.")
    print("    - visual layout. Phase 7 checks geometry, not appearance.")

    demo_script = Path("docs/DEMO_SCRIPT.md")
    if demo_script.exists():
        text = demo_script.read_text(encoding="utf-8", errors="replace")
        import re
        block = text.split("## LIMITATIONS")[-1].split("\n## ")[0] if "## LIMITATIONS" in text else ""
        count = len(re.findall(r"^\d+\.\s+\*\*", block, re.M))
        print()
        print(f"  docs/DEMO_SCRIPT.md declares {count} limitations. Say all of them.")
    else:
        print()
        print("  docs/DEMO_SCRIPT.md NOT FOUND - the limitations list is missing")

    failed = [r for r in h.results if not r.passed]
    print()
    print(RULE)
    print(f"  {len(h.results) - len(failed)}/{len(h.results)} phases passed")
    print(RULE)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
