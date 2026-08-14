"""Rename student answer scripts to opaque IDs, before anything reads them.

Filenames are the exposure. `CS2024003_3faeea7a.pdf` puts a roll number into
every directory listing, log line, stack trace, and error message that touches
the path -- the same shape as the token-in-query-string finding, where the
identifier ended up somewhere nobody was thinking about. Redacting page content
does not help if the filename is the leak.

So this runs BEFORE the harness, before OCR, before anything opens a file.

SAFETY MODEL
------------
* Dry run is the default. Nothing is written without --execute.
* The mapping file must live OUTSIDE the working tree, is passed explicitly,
  and the script refuses to run if it resolves inside the repo.
* Copy, then verify by SHA-256, then delete. Never `mv`: a rename that fails
  part-way through leaves no way to tell which files moved.
* Refuses to overwrite an existing mapping unless --resume, so a second
  accidental run cannot orphan the first run's mapping and strand every file.
* After executing, sweeps the whole tree for surviving roll-number tokens --
  in filenames AND inside text files that reference them -- and reports a
  non-zero exit if any survive.

    python -m scripts.anonymize_scripts --mapping C:/private/grademind_map.json
    python -m scripts.anonymize_scripts --mapping /abs/path/map.json --execute
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_ROOT = Path("backend/storage")

# 2-4 letters followed by 2-10 digits: CS005, CS2024003, PHY12.
#
# NOT \b at the edges. An underscore is a word character, so \b never fires
# between "005" and "_" -- and every filename here is `CS005_fe7deca0.pdf`.
# The first version of this pattern reported "0 roll tokens found" against
# 1219 files that visibly contain them, which would have made the
# post-execution sweep declare success while the identifiers survived.
# Explicit alphanumeric lookarounds instead.
ROLL_TOKEN = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{2,4}\d{2,10}(?![A-Za-z0-9])")

# Files whose CONTENT is worth sweeping for roll tokens after the rename.
TEXTUAL = {".json", ".txt", ".csv", ".md", ".log", ".jsonl", ".xml", ".html"}

CHUNK = 1024 * 1024


@dataclass
class Plan:
    old_path: str
    old_name: str
    roll_tokens: List[str]
    new_name: str
    new_path: str
    size_bytes: int
    sha256: str


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def opaque_id() -> str:
    """Random, not sequential.

    S001, S002... would leak ordering, and ordering in an exam directory is
    usually roll order, which is most of what the rename is removing.
    """
    return "S_" + secrets.token_hex(8)


def discover(root: Path) -> List[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and p.name != ".gitkeep")


def build_plan(root: Path, taken: Optional[set] = None) -> List[Plan]:
    taken = taken if taken is not None else set()
    plans: List[Plan] = []

    for path in discover(root):
        tokens = sorted(set(ROLL_TOKEN.findall(path.stem)))

        while True:
            new_stem = opaque_id()
            if new_stem not in taken:
                taken.add(new_stem)
                break

        new_name = new_stem + path.suffix.lower()
        plans.append(
            Plan(
                old_path=str(path),
                old_name=path.name,
                roll_tokens=tokens,
                new_name=new_name,
                new_path=str(path.parent / new_name),
                size_bytes=path.stat().st_size,
                sha256="(not computed in dry run)",
            )
        )

    return plans


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------


def validate_mapping_path(mapping: Path, resume: bool) -> Optional[str]:
    """Returns an error string, or None if the path is acceptable."""
    if not mapping.is_absolute():
        return (
            f"mapping path must be absolute, got {mapping!s}. "
            "A relative path is too easy to land inside the repo."
        )

    resolved = mapping.resolve()
    repo = Path.cwd().resolve()
    try:
        resolved.relative_to(repo)
    except ValueError:
        pass  # outside the tree, which is what we want
    else:
        return (
            f"mapping file {resolved} is INSIDE the working tree ({repo}). "
            "The ID-to-student mapping must never live in the repository. "
            "Pass a path outside it."
        )

    if resolved.exists() and not resume:
        return (
            f"mapping file already exists: {resolved}\n"
            "Refusing to overwrite it. A second run would orphan the first "
            "run's mapping and strand every already-renamed file. Use "
            "--resume only if you are continuing an interrupted run."
        )

    parent = resolved.parent
    if not parent.exists():
        return f"mapping directory does not exist: {parent}"

    return None


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def execute(plans: Sequence[Plan], mapping_path: Path) -> Tuple[int, List[str]]:
    """Copy -> verify -> delete, one file at a time. Returns (done, errors)."""
    import shutil

    done = 0
    errors: List[str] = []
    records: List[dict] = []

    for plan in plans:
        src = Path(plan.old_path)
        dst = Path(plan.new_path)

        if not src.exists():
            errors.append(f"source vanished: {src}")
            continue
        if dst.exists():
            errors.append(f"destination already exists, skipping: {dst}")
            continue

        try:
            source_hash = sha256_of(src)
            shutil.copy2(src, dst)

            # Verify BEFORE deleting. A copy that silently truncated is the
            # failure this ordering exists to prevent.
            dest_hash = sha256_of(dst)
            if dest_hash != source_hash:
                errors.append(
                    f"HASH MISMATCH after copy, source kept: {src} "
                    f"({source_hash[:12]} != {dest_hash[:12]})"
                )
                dst.unlink(missing_ok=True)
                continue

            os.remove(src)

            plan.sha256 = source_hash
            records.append(asdict(plan))
            done += 1

        except OSError as exc:
            errors.append(f"{src}: {exc}")

        # Write the mapping after EVERY file, not at the end. An interrupted
        # run must leave a mapping that covers exactly what was moved.
        _write_mapping(mapping_path, records)

    return done, errors


def _write_mapping(path: Path, records: List[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "_warning": [
                    "This file maps opaque IDs to original student filenames.",
                    "It is the re-identification key. Treat it as the most",
                    "sensitive artefact in the project. Never commit it.",
                ],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "count": len(records),
                "mappings": records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Post-execution sweep
# ---------------------------------------------------------------------------


def sweep(root: Path, tokens: Sequence[str]) -> Dict[str, List[str]]:
    """Find surviving roll tokens in filenames and in text file contents."""
    findings: Dict[str, List[str]] = {"filenames": [], "contents": []}
    if not tokens:
        return findings

    token_set = {t.lower() for t in tokens}

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if {t.lower() for t in ROLL_TOKEN.findall(path.stem)} & token_set:
            findings["filenames"].append(str(path))

        if path.suffix.lower() in TEXTUAL:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            hits = {t.lower() for t in ROLL_TOKEN.findall(text)} & token_set
            if hits:
                findings["contents"].append(f"{path}  ({', '.join(sorted(hits))})")

    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--mapping", type=Path, required=True,
                        help="ABSOLUTE path, outside the repo, for the ID map")
    parser.add_argument("--execute", action="store_true",
                        help="actually rename. Without this, nothing is written.")
    parser.add_argument("--resume", action="store_true",
                        help="continue an interrupted run into an existing mapping")
    parser.add_argument("--limit", type=int, default=0,
                        help="show only the first N entries in the dry-run plan")
    args = parser.parse_args(argv[1:])

    W = 76
    print("=" * W)
    print("  ANONYMIZE ANSWER SCRIPTS" + ("  [EXECUTE]" if args.execute else "  [DRY RUN - nothing will be written]"))
    print("=" * W)

    error = validate_mapping_path(args.mapping, args.resume)
    if error:
        print(f"\n  REFUSING TO RUN\n\n  {error}\n", file=sys.stderr)
        return 2

    if not args.root.exists():
        print(f"\n  root does not exist: {args.root}\n")
        return 2

    plans = build_plan(args.root)
    if not plans:
        print(f"\n  no files under {args.root}\n")
        return 0

    with_tokens = [p for p in plans if p.roll_tokens]
    all_tokens = sorted({t for p in plans for t in p.roll_tokens})
    total_bytes = sum(p.size_bytes for p in plans)

    print(f"\n  root            : {args.root}")
    print(f"  mapping         : {args.mapping}  (outside repo: OK)")
    print(f"  files found     : {len(plans)}")
    print(f"  with roll tokens: {len(with_tokens)}")
    print(f"  distinct tokens : {len(all_tokens)}")
    print(f"  total size      : {total_bytes / (1024*1024):.1f} MB")

    print(f"\n  PLAN ({'first ' + str(args.limit) if args.limit else 'all'} entries)")
    print("  " + "-" * (W - 4))
    shown = plans[: args.limit] if args.limit else plans
    for p in shown:
        marker = "*" if p.roll_tokens else " "
        print(f"  {marker} {p.old_name}")
        print(f"      -> {p.new_name}   ({p.size_bytes:,} bytes)")
        if p.roll_tokens:
            print(f"      roll tokens removed from name: {', '.join(p.roll_tokens)}")
    if args.limit and len(plans) > args.limit:
        print(f"  ... and {len(plans) - args.limit} more")

    if not args.execute:
        print("\n" + "=" * W)
        print("  DRY RUN COMPLETE - nothing was written, nothing was renamed.")
        print(f"  Re-run with --execute to perform {len(plans)} copy-verify-delete operations.")
        print("  The mapping is the re-identification key. Keep it out of the repo,")
        print("  out of backups that sync to the repo, and out of chat.")
        print("=" * W)
        return 0

    print("\n  EXECUTING (copy -> verify sha256 -> delete)")
    done, errors = execute(plans, args.mapping)
    print(f"  renamed {done}/{len(plans)} files")

    if errors:
        print(f"\n  {len(errors)} ERROR(S):")
        for e in errors:
            print(f"    {e}")

    print("\n  SWEEP: surviving roll tokens anywhere under the root")
    findings = sweep(args.root, all_tokens)
    if findings["filenames"] or findings["contents"]:
        print(f"    filenames: {len(findings['filenames'])}")
        for f in findings["filenames"][:20]:
            print(f"      {f}")
        print(f"    file contents: {len(findings['contents'])}")
        for f in findings["contents"][:20]:
            print(f"      {f}")
        print("\n  NOT CLEAN. Roll numbers survive. Content inside files is not")
        print("  rewritten by this tool - that is a separate, riskier operation.")
        print("=" * W)
        return 1

    print("    none found")
    print("\n" + "=" * W)
    print("  Clean. Mapping written to the path above. Back it up somewhere")
    print("  that is not this repository, then verify you can still re-identify")
    print("  a script before deleting anything else.")
    print("=" * W)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
