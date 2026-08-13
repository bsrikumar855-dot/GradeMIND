"""Fail if a test skips itself unconditionally or from inside its own body.

Two patterns this catches, both present in AI/tests before Phase 0:

  * ``pytest.skip(...)`` called inside a test function body. In
    test_or_question_resolver.py:321 this sat in the ``else`` branch of an
    assertion — a failing case reported as a skip.
  * ``@pytest.mark.skipif(True, ...)`` or ``@pytest.mark.skip``, which turns
    the suite green without running anything.

Module-level ``pytest.importorskip`` and ``skipif`` guarded by a real runtime
condition (a missing optional engine, a platform check) are legitimate and are
not flagged.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterator, List, Tuple

Finding = Tuple[Path, int, str, str]  # path, line, message, kind

TEST_DIRS = ("AI/tests", "backend/tests")


def _is_pytest_skip(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "skip"
        and isinstance(func.value, ast.Name)
        and func.value.id == "pytest"
    )


def _is_unconditional_skip_marker(node: ast.expr) -> str | None:
    """Return a reason if the decorator is an always-on skip."""
    call = node if isinstance(node, ast.Call) else None
    target = call.func if call else node

    if not isinstance(target, ast.Attribute):
        return None

    # @pytest.mark.skip / @pytest.mark.skip(...)
    if target.attr == "skip":
        return "@pytest.mark.skip"

    # @pytest.mark.skipif(True, ...)
    if target.attr == "skipif" and call and call.args:
        first = call.args[0]
        if isinstance(first, ast.Constant) and first.value is True:
            return "@pytest.mark.skipif(True, ...)"

    return None


def _is_xfail_marker(node: ast.expr) -> str | None:
    """Return a reason if the decorator is an xfail.

    Tracked because xfail is a suppression mechanism too, and this checker
    would otherwise create a loophole: removing a tracked `skipif` and adding
    an untracked `xfail` would be a net loss in the coverage this script
    exists to provide.

    Counted separately from skips in the baseline — they mean different
    things. A skip does not run. An xfail runs, is expected to fail, and with
    strict=True fails the build if it ever passes. A non-strict xfail is much
    closer to a skip and is flagged as such.
    """
    call = node if isinstance(node, ast.Call) else None
    target = call.func if call else node

    if not isinstance(target, ast.Attribute) or target.attr != "xfail":
        return None

    strict = False
    if call:
        for kw in call.keywords:
            if kw.arg == "strict" and isinstance(kw.value, ast.Constant):
                strict = bool(kw.value.value)

    if strict:
        return "@pytest.mark.xfail(strict=True)"
    return "@pytest.mark.xfail (NOT strict — can silently start passing)"


def _walk_tests(tree: ast.AST) -> Iterator[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            if name.startswith("test") or name.startswith("Test"):
                yield node


def check_file(path: Path) -> List[Finding]:
    findings: List[Finding] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [(path, exc.lineno or 0, f"could not parse: {exc.msg}", "skip")]

    for node in _walk_tests(tree):
        for decorator in getattr(node, "decorator_list", []):
            reason = _is_unconditional_skip_marker(decorator)
            if reason:
                findings.append(
                    (path, decorator.lineno, f"{node.name} is disabled by {reason}", "skip")
                )
                continue

            xfail_reason = _is_xfail_marker(decorator)
            if xfail_reason:
                findings.append(
                    (path, decorator.lineno, f"{node.name} is {xfail_reason}", "xfail")
                )

        if isinstance(node, ast.ClassDef):
            continue

        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and _is_pytest_skip(inner):
                findings.append(
                    (
                        path,
                        inner.lineno,
                        f"{node.name} calls pytest.skip() in its own body — "
                        "assert or delete the case instead",
                        "skip",
                    )
                )

    return findings


def _key(path: Path, message: str, kind: str) -> str:
    """Identity of a finding, deliberately excluding the line number.

    Editing a file above a known suppression must not look like a new one.
    The kind is part of the identity so that converting a skip into an xfail
    shows up as one entry leaving and another arriving, rather than silently
    reusing the same slot.
    """
    test_name = message.split(" ", 1)[0]
    return f"{kind}:{path.as_posix()}::{test_name}"


def _load_baseline(path: Path) -> set:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def main(argv: List[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    write_baseline = "--write-baseline" in argv

    roots = [Path(p) for p in args] or [Path(d) for d in TEST_DIRS]
    baseline_path = Path("scripts/self_skipping_tests_baseline.txt")

    findings: List[Finding] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("test_*.py")):
            findings.extend(check_file(path))

    current = {_key(p, m, k) for p, _, m, k in findings}

    def _counts(keys):
        skips = sum(1 for k in keys if k.startswith("skip:"))
        xfails = sum(1 for k in keys if k.startswith("xfail:"))
        return skips, xfails

    if write_baseline:
        skips, xfails = _counts(current)
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(
            "# Known suppressed tests. This list may shrink, never grow —\n"
            "# a new entry fails CI. Remove a line by making the test assert,\n"
            "# fixing what it caught, or deleting it.\n"
            "#\n"
            "# Two kinds, counted separately because they mean different things:\n"
            "#\n"
            "#   skip:   does not run at all. Nothing is verified.\n"
            "#   xfail:  runs, is expected to fail, and with strict=True fails\n"
            "#           the build if it ever passes. A declared defect with a\n"
            "#           reason attached, not a hidden one.\n"
            "#\n"
            f"# Current: {skips} skip, {xfails} xfail. Target: 0 skip by end of Track C.\n"
            + "\n".join(sorted(current))
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(current)} entries ({skips} skip, {xfails} xfail) to {baseline_path}")
        return 0

    baseline = _load_baseline(baseline_path)
    new = current - baseline

    if new:
        for path, line, message, kind in findings:
            if _key(path, message, kind) in new:
                print(f"{path}:{line}: [{kind}] {message}", file=sys.stderr)
        new_skips, new_xfails = _counts(new)
        print(
            f"\n{len(new)} NEW suppressed test(s) — {new_skips} skip, "
            f"{new_xfails} xfail. The baseline in {baseline_path} may shrink, "
            "never grow.",
            file=sys.stderr,
        )
        return 1

    resolved = baseline - current
    if resolved:
        print(f"{len(resolved)} baselined suppression(s) resolved — remove from baseline:")
        for entry in sorted(resolved):
            print(f"  {entry}")

    skips, xfails = _counts(current)
    print(f"no new suppressed tests ({skips} skip, {xfails} xfail baselined)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
