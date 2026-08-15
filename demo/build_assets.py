"""Copy the real annotated renders into demo/assets and assert they are real.

The demo page shows actual handwriting with actual highlights drawn by our own
annotator. Those renders are produced into tmp/, which is gitignored, so
without this step a fresh clone gets a page with broken images and no warning.

An empty page because a gitignored file vanished is exactly the failure that
shows up in the room, so this asserts rather than copies quietly:

  * the source render exists and is non-zero
  * it is actually a PNG, by magic bytes rather than by extension
  * it has plausible dimensions for a 150 dpi A4 page
  * the copy that lands in assets/ is byte-identical to the source

    python demo/build_assets.py            # copy and verify
    python demo/build_assets.py --check    # verify only, exit 1 if wrong
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "demo" / "assets"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MIN_BYTES = 50_000  # a real 150 dpi page render is ~0.8 MB; this catches stubs

SOURCES = {
    "annotated-page-2.png": ROOT / "tmp" / "verify_page2.png",
    "annotated-page-3.png": ROOT / "tmp" / "verify_page3.png",
}


def png_dimensions(data: bytes) -> tuple[int, int]:
    """Read width and height out of the IHDR chunk."""
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def verify(path: Path, label: str) -> list[str]:
    problems: list[str] = []
    if not path.exists():
        return [f"{label}: MISSING at {path}"]

    data = path.read_bytes()
    if len(data) < MIN_BYTES:
        problems.append(f"{label}: only {len(data):,} bytes, expected >{MIN_BYTES:,}")
    if not data.startswith(PNG_MAGIC):
        problems.append(f"{label}: not a PNG (magic bytes {data[:8]!r})")
        return problems

    w, h = png_dimensions(data)
    if not (800 <= w <= 2000 and 1000 <= h <= 2600):
        problems.append(f"{label}: implausible dimensions {w}x{h} for a page render")
    return problems


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    ASSETS.mkdir(parents=True, exist_ok=True)

    problems: list[str] = []
    print(f"{'asset':<26} {'bytes':>10}  {'dims':>11}  status")

    for name, source in SOURCES.items():
        target = ASSETS / name

        if not check_only:
            if not source.exists():
                problems.append(
                    f"{name}: source render {source} is missing. Run\n"
                    f"    PYTHONPATH=. python -m scripts.verify_demo\n"
                    f"  which regenerates it, then re-run this script."
                )
                print(f"{name:<26} {'-':>10}  {'-':>11}  SOURCE MISSING")
                continue
            shutil.copy2(source, target)

        found = verify(target, name)
        problems.extend(found)

        if target.exists():
            data = target.read_bytes()
            w, h = png_dimensions(data) if data.startswith(PNG_MAGIC) else (0, 0)
            print(f"{name:<26} {len(data):>10,}  {f'{w}x{h}':>11}  "
                  f"{'OK' if not found else 'FAIL'}")

            if not check_only and SOURCES[name].exists():
                src_hash = hashlib.sha256(SOURCES[name].read_bytes()).hexdigest()
                dst_hash = hashlib.sha256(data).hexdigest()
                if src_hash != dst_hash:
                    problems.append(f"{name}: copy does not match source")
        else:
            print(f"{name:<26} {'-':>10}  {'-':>11}  MISSING")

    print()
    if problems:
        print("ASSET CHECK FAILED:")
        for p in problems:
            print(f"  {p}")
        print("\nThe demo page shows real renders of a real script. It must not")
        print("ship with broken or placeholder images.")
        return 1

    print("All assets present, real PNGs, plausible dimensions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
