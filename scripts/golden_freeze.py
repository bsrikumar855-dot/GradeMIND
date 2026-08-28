#!/usr/bin/env python3
"""Freeze the golden set: hash every file, record the time, assert no engine has run.

The freeze is what lets you prove later that the ground truth predates any
engine result. Nobody plans to adjust ground truth after seeing what the engine
said. People do it anyway, a mark at a time, telling themselves the engine had a
point. A committed manifest makes that visible instead of invisible.

Usage:
    python scripts/golden_freeze.py golden/
    python scripts/golden_freeze.py golden/ --verify   # check, do not rewrite

Exit codes:
    0  frozen (or verified unchanged)
    1  refused, or verification found a difference
    2  usage error
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

MANIFEST_NAME = "MANIFEST.sha256"

# Engine output. If any of these appear in a marks file the set is not blind.
ENGINE_FIELDS = ("engine_mark_A", "engine_mark_B", "ocr_confidence")

# Files that are hashed. Scans are deliberately absent -- they live outside the
# repository with id_mapping.csv, and metadata.json carries their SHA-256.
HASHED_SUFFIXES = {".json", ".jsonl", ".txt", ".md", ".csv"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect(root: Path) -> List[Path]:
    files = [
        p
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix in HASHED_SUFFIXES and p.name != MANIFEST_NAME
    ]
    return files


def _assert_no_identity_files(root: Path) -> List[str]:
    """The ID mapping must never be inside the repository. Protocol section 1.3."""
    problems = []
    for p in root.rglob("*"):
        if p.is_file() and p.name.lower() in {"id_mapping.csv", "id-mapping.csv"}:
            problems.append(
                f"{p} is inside the repository. The identity mapping lives on encrypted "
                "storage OUTSIDE the repo, always. Remove it, and if it was ever "
                "committed, treat that as a disclosure incident."
            )
    return problems


def _assert_engine_has_not_run(root: Path) -> List[str]:
    """Refuse to freeze a set that already carries engine marks."""
    problems = []
    for p in sorted(root.rglob("*.jsonl")):
        try:
            with open(p, encoding="utf-8") as fh:
                for lineno, raw in enumerate(fh, 1):
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError as exc:
                        problems.append(f"{p}:{lineno}: not valid JSON: {exc}")
                        continue
                    if not isinstance(row, dict):
                        continue
                    present = [f for f in ENGINE_FIELDS if f in row]
                    if present:
                        problems.append(
                            f"{p}:{lineno}: carries engine output {present}. The freeze "
                            "records ground truth BEFORE the engine runs. Remove these "
                            "fields, or if the engine really has already been run "
                            "against this script, the script is no longer blind ground "
                            "truth and must be discarded."
                        )
        except OSError as exc:
            problems.append(f"{p}: cannot read: {exc}")
    return problems


def _read_manifest(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("files", {}))


def _build(root: Path) -> Tuple[Dict[str, str], List[Path]]:
    files = _collect(root)
    digests = {str(p.relative_to(root)).replace("\\", "/"): _sha256(p) for p in files}
    return digests, files


def freeze(root: Path, verify_only: bool) -> int:
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    problems = _assert_no_identity_files(root) + _assert_engine_has_not_run(root)
    if problems:
        print("REFUSED. The set cannot be frozen:")
        for p in problems:
            print(f"  - {p}")
        return 1

    digests, files = _build(root)
    if not digests:
        print(f"error: no files to hash under {root}", file=sys.stderr)
        return 2

    manifest_path = root / MANIFEST_NAME

    if verify_only:
        if not manifest_path.exists():
            print(f"error: {manifest_path} does not exist; nothing to verify", file=sys.stderr)
            return 1
        recorded = _read_manifest(manifest_path)
        added = sorted(set(digests) - set(recorded))
        removed = sorted(set(recorded) - set(digests))
        changed = sorted(f for f in set(digests) & set(recorded) if digests[f] != recorded[f])
        if not (added or removed or changed):
            print(f"VERIFIED unchanged: {len(digests)} files match {MANIFEST_NAME}")
            return 0
        print("VERIFICATION FAILED -- the frozen set has changed:")
        for f in changed:
            print(f"  CHANGED  {f}")
        for f in added:
            print(f"  ADDED    {f}")
        for f in removed:
            print(f"  REMOVED  {f}")
        print(
            "\nIf this change is legitimate -- a genuine transcription error, a misread "
            "scheme --\nrecord what changed and why, re-run the freeze, and commit the new "
            "manifest as its\nown commit with the reason in the message. An unexplained "
            "change here is\nindistinguishable from tuning the answers to fit the engine."
        )
        return 1

    scripts = sorted({p.parent.name for p in files if p.name == "marks.jsonl"})
    second = sorted({p.parent.name for p in files if p.name == "second_marks.jsonl"})

    manifest = {
        "_comment": [
            "Frozen ground truth for the GradeMIND golden set.",
            "engine_not_yet_run: true means no engine output existed when this was written.",
            "Verify with: python scripts/golden_freeze.py golden/ --verify",
            "See docs/GOLDEN_SET_PROTOCOL.md.",
        ],
        "frozen_at_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "engine_not_yet_run": True,
        "script_count": len(scripts),
        "second_marked_count": len(second),
        "scripts": scripts,
        "second_marked": second,
        "algorithm": "sha256",
        "files": digests,
    }

    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"FROZEN  {manifest_path}")
    print(f"  files hashed:   {len(digests)}")
    print(f"  scripts:        {len(scripts)}")
    print(f"  second-marked:  {len(second)}")
    print(f"  frozen_at_utc:  {manifest['frozen_at_utc']}")
    print()
    if len(second) < 10:
        print(
            f"WARNING: only {len(second)} scripts are second-marked. Below 10, the "
            "human-human\nceiling is too noisy to interpret an agreement figure against."
        )
        print()
    print("Commit this manifest now. That commit is the proof the ground truth")
    print("predates any engine result. Only then run the engine.")
    return 0


def main(argv: List[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}

    unknown = flags - {"--verify"}
    if unknown:
        print(f"error: unknown flag(s): {sorted(unknown)}", file=sys.stderr)
        return 2
    if len(args) != 1:
        print(__doc__)
        return 2

    return freeze(Path(args[0]), verify_only="--verify" in flags)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
