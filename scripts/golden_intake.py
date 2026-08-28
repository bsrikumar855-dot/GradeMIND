#!/usr/bin/env python3
"""Validate a submitted golden-set script folder against docs/GOLDEN_SET_PROTOCOL.md.

Refuses anything incomplete and says exactly what is missing. It never repairs,
never fills in a default, and never accepts a folder "with warnings": a golden
set is the measuring instrument, and an instrument that accepts partial input
produces a number that will be believed.

Usage:
    python scripts/golden_intake.py golden/scripts/S001
    python scripts/golden_intake.py golden/scripts/*
    python scripts/golden_intake.py golden/          # every script under it

Exit codes:
    0  every folder valid
    1  at least one folder rejected
    2  usage error
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

SCRIPT_ID_RE = re.compile(r"^S\d{3,}$")
QUESTION_HEADING_RE = re.compile(r"^\[Q([0-9]+[a-z]?)\]$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_MARK_FIELDS = ("script_id", "question_number", "max_marks", "human_mark")

# Written by the engine, after the freeze. Their presence in a submitted folder
# means either the engine has already been run against this script or somebody
# is filling them in by hand. Both invalidate the script, so this is a
# rejection and not a warning.
FORBIDDEN_MARK_FIELDS = ("engine_mark_A", "engine_mark_B", "ocr_confidence")

KNOWN_MARK_FIELDS = set(REQUIRED_MARK_FIELDS) | {
    "subject",
    "question_type",
    "second_human_mark",
}

REQUIRED_METADATA_FIELDS = (
    "script_id",
    "subject",
    "exam",
    "pages",
    "scan_sha256",
    "anonymised",
    "consent_reference",
)


@dataclass
class Result:
    """Findings for one script folder."""

    folder: Path
    errors: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_json(path: Path, res: Result) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        res.error(f"{path.name} is missing")
    except json.JSONDecodeError as exc:
        res.error(f"{path.name} is not valid JSON: {exc}")
    return None


def _load_jsonl(path: Path, res: Result) -> Optional[List[Dict[str, Any]]]:
    """Load JSONL. A malformed line is an error, never a skipped row."""
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("[") or line.endswith(","):
                    res.error(
                        f"{path.name}:{lineno}: looks like a JSON array. This file is "
                        "JSONL: one object per line, no enclosing brackets, no "
                        "trailing commas."
                    )
                    return None
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    res.error(f"{path.name}:{lineno}: not valid JSON: {exc}")
                    return None
                if not isinstance(obj, dict):
                    res.error(f"{path.name}:{lineno}: expected an object, got {type(obj).__name__}")
                    return None
                rows.append(obj)
    except FileNotFoundError:
        res.error(f"{path.name} is missing")
        return None
    return rows


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_metadata(folder: Path, res: Result) -> Optional[Dict[str, Any]]:
    meta = _load_json(folder / "metadata.json", res)
    if meta is None:
        return None

    for fieldname in REQUIRED_METADATA_FIELDS:
        if fieldname not in meta:
            res.error(f"metadata.json: required field '{fieldname}' is missing")

    script_id = meta.get("script_id")
    if script_id is not None:
        if not isinstance(script_id, str) or not SCRIPT_ID_RE.match(script_id):
            res.error(
                f"metadata.json: script_id {script_id!r} must look like 'S001' -- "
                "an S and at least three digits, carrying no information about the student"
            )
        elif script_id != folder.name:
            res.error(
                f"metadata.json: script_id {script_id!r} does not match folder name "
                f"{folder.name!r}"
            )

    # Anonymisation is a gate, not a field. See protocol section 1.
    if meta.get("anonymised") is not True:
        res.error(
            "metadata.json: anonymised must be exactly true. A script that has not been "
            "through the masking pass in protocol section 1 cannot be accepted -- that "
            "includes masking any previous examiner's margin marks."
        )

    sha = meta.get("scan_sha256")
    if sha is not None and (not isinstance(sha, str) or not SHA256_RE.match(sha)):
        res.error(
            f"metadata.json: scan_sha256 {sha!r} is not a 64-character lowercase hex "
            "SHA-256. It links the committed record to the scan without committing the scan."
        )

    pages = meta.get("pages")
    if pages is not None and (not isinstance(pages, int) or pages < 1):
        res.error(f"metadata.json: pages must be a positive integer, got {pages!r}")

    return meta


def check_transcription(folder: Path, res: Result) -> Set[str]:
    """Return the set of question numbers found in transcription.txt."""
    path = folder / "transcription.txt"
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        res.error("transcription.txt is missing")
        return set()
    except UnicodeDecodeError as exc:
        res.error(f"transcription.txt is not valid UTF-8: {exc}")
        return set()

    if not text.strip():
        res.error("transcription.txt is empty")
        return set()

    found: List[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped.startswith("[Q"):
            continue
        m = QUESTION_HEADING_RE.match(stripped)
        if not m:
            res.error(
                f"transcription.txt:{lineno}: {stripped!r} is not a valid question "
                "heading. Use [Q1] or [Q4a] on a line of its own."
            )
            continue
        found.append(m.group(1))

    if not found:
        res.error(
            "transcription.txt contains no [Qn] headings. Each question's answer must be "
            "headed by its number on a line of its own."
        )

    dupes = {q for q in found if found.count(q) > 1}
    if dupes:
        res.error(f"transcription.txt: duplicate question headings: {sorted(dupes)}")

    return set(found)


def check_marks(
    path: Path,
    res: Result,
    expected_script_id: Optional[str],
    label: str,
) -> Optional[Dict[str, Tuple[float, float]]]:
    """Validate one marks file. Returns {question_number: (human_mark, max_marks)}."""
    rows = _load_jsonl(path, res)
    if rows is None:
        return None
    if not rows:
        res.error(f"{path.name} is empty. Every question needs a row, including unattempted ones.")
        return None

    marks: Dict[str, Tuple[float, float]] = {}

    for i, row in enumerate(rows, 1):
        where = f"{path.name}:{i}"

        for fieldname in REQUIRED_MARK_FIELDS:
            if fieldname not in row:
                res.error(f"{where}: required field '{fieldname}' is missing")

        present_forbidden = [f for f in FORBIDDEN_MARK_FIELDS if f in row]
        if present_forbidden:
            res.error(
                f"{where}: contains {present_forbidden}. These are written by the engine "
                "AFTER the freeze. Their presence means the engine has already been run "
                "against this script, or somebody is filling them in by hand. Either way "
                "the script cannot serve as blind ground truth."
            )

        unknown = set(row) - KNOWN_MARK_FIELDS - set(FORBIDDEN_MARK_FIELDS)
        if unknown:
            res.error(
                f"{where}: unrecognised field(s) {sorted(unknown)}. The harness ignores "
                "unknown fields, so a typo like 'human_marks' would silently become a "
                "missing mark."
            )

        sid = row.get("script_id")
        if expected_script_id and sid != expected_script_id:
            res.error(f"{where}: script_id {sid!r} should be {expected_script_id!r}")

        qnum = row.get("question_number")
        if qnum is not None and not isinstance(qnum, str):
            res.error(
                f"{where}: question_number must be a string ({qnum!r} -> \"{qnum}\"). "
                "Question numbers like '4a' are not numeric, so the field is a string "
                "throughout."
            )
            qnum = str(qnum)

        maxm = row.get("max_marks")
        hum = row.get("human_mark")

        if not isinstance(maxm, (int, float)) or isinstance(maxm, bool):
            res.error(f"{where}: max_marks must be a number, got {maxm!r}")
            continue
        if not isinstance(hum, (int, float)) or isinstance(hum, bool):
            res.error(f"{where}: human_mark must be a number, got {hum!r}")
            continue

        maxm, hum = float(maxm), float(hum)

        if maxm <= 0:
            res.error(f"{where}: max_marks must be positive, got {maxm}")
        if hum < 0:
            res.error(f"{where}: human_mark {hum} is negative")
        elif hum > maxm:
            res.error(
                f"{where}: human_mark {hum} exceeds max_marks {maxm} for question {qnum}"
            )

        # Quarter marks are almost always a slip or an averaged disagreement.
        if abs((hum * 2) - round(hum * 2)) > 1e-9:
            res.error(
                f"{where}: human_mark {hum} is not a whole or half mark. Marks must land "
                "on the scheme's own granularity; a quarter mark usually means two "
                "markers were averaged, which destroys the ceiling measurement."
            )

        if qnum is not None:
            if qnum in marks:
                res.error(f"{where}: question {qnum} appears more than once in {label}")
            marks[str(qnum)] = (hum, maxm)

    return marks


def check_folder(folder: Path) -> Result:
    res = Result(folder=folder)

    if not folder.is_dir():
        res.error(f"{folder} is not a directory")
        return res

    meta = check_metadata(folder, res)
    script_id = meta.get("script_id") if meta else None
    transcribed = check_transcription(folder, res)

    first = check_marks(folder / "marks.jsonl", res, script_id, "marks.jsonl")

    second_path = folder / "second_marks.jsonl"
    second: Optional[Dict[str, Tuple[float, float]]] = None
    if second_path.exists():
        second = check_marks(second_path, res, script_id, "second_marks.jsonl")
    else:
        res.note(
            "no second_marks.jsonl -- optional per script, but at least 10 scripts in the "
            "set must have one. Human-human agreement is the ceiling on what "
            "machine-human agreement can mean."
        )

    # Cross-file consistency.
    if first and transcribed:
        marked = set(first)
        missing = sorted(transcribed - marked)
        extra = sorted(marked - transcribed)
        if missing:
            res.error(
                f"transcribed but not marked: {missing}. Every question in the "
                "transcription needs a row, including unattempted ones at 0.0 -- an "
                "omitted row and a zero are different statements."
            )
        if extra:
            res.error(f"marked but not present in transcription.txt: {extra}")

    if first and second:
        if set(first) != set(second):
            only_first = sorted(set(first) - set(second))
            only_second = sorted(set(second) - set(first))
            res.error(
                "marks.jsonl and second_marks.jsonl cover different questions "
                f"(only in first: {only_first}; only in second: {only_second}). "
                "The second marker must mark the same questions from the same "
                "transcription."
            )
        for q in sorted(set(first) & set(second)):
            if abs(first[q][1] - second[q][1]) > 1e-9:
                res.error(
                    f"question {q}: max_marks differs between markers "
                    f"({first[q][1]} vs {second[q][1]}). Both must come from the same "
                    "official scheme."
                )
        agree = sum(1 for q in set(first) & set(second) if abs(first[q][0] - second[q][0]) < 1e-9)
        total = len(set(first) & set(second))
        if total:
            res.note(f"two markers agree exactly on {agree}/{total} questions")
            if agree == total and total >= 4:
                res.note(
                    "markers agree on every question. Worth confirming they marked "
                    "independently -- perfect agreement is possible but uncommon, and it "
                    "is what contaminated second marking looks like."
                )

    return res


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _expand(targets: List[str]) -> List[Path]:
    """A bare golden/ or golden/scripts/ expands to the script folders under it."""
    folders: List[Path] = []
    for t in targets:
        p = Path(t)
        if not p.exists():
            print(f"error: {p} does not exist", file=sys.stderr)
            continue
        if p.is_dir() and (p / "metadata.json").exists():
            folders.append(p)
            continue
        if p.is_dir():
            nested = p / "scripts"
            search = nested if nested.is_dir() else p
            found = sorted(c for c in search.iterdir() if (c / "metadata.json").exists())
            if found:
                folders.extend(found)
            else:
                print(f"error: no script folders found under {p}", file=sys.stderr)
    return folders


def main(argv: List[str]) -> int:
    if not argv:
        print(__doc__)
        return 2

    folders = _expand(argv)
    if not folders:
        print("no script folders to validate", file=sys.stderr)
        return 2

    results = [check_folder(f) for f in folders]

    for res in results:
        if res.ok:
            print(f"PASS  {res.folder}")
        else:
            print(f"FAIL  {res.folder}")
            for e in res.errors:
                print(f"        - {e}")
        for n in res.notes:
            print(f"        note: {n}")

    passed = sum(1 for r in results if r.ok)
    failed = len(results) - passed
    print()
    print(f"{passed} passed, {failed} rejected")

    if failed:
        print()
        print("Nothing was repaired. Fix the folders above and re-run.")
        return 1

    with_second = sum(1 for f in folders if (f / "second_marks.jsonl").exists())
    print()
    print(f"scripts: {len(folders)}   second-marked: {with_second}")
    if with_second < 10:
        print(
            f"NOT READY TO FREEZE: {with_second} second-marked, at least 10 required.\n"
            "  Without human-human agreement an agreement figure cannot be interpreted:\n"
            "  62% is poor if two humans agree 95% of the time and near the ceiling if\n"
            "  they agree 64% of the time. Same number, opposite conclusions."
        )
        return 1
    if len(folders) < 10:
        print(f"NOT READY TO FREEZE: {len(folders)} scripts, at least 10 required.")
        return 1

    print("Ready to freeze:  python scripts/golden_freeze.py golden/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
