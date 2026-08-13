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

Finding = Tuple[Path, int, str]

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
        return [(path, exc.lineno or 0, f"could not parse: {exc.msg}")]

    for node in _walk_tests(tree):
        for decorator in getattr(node, "decorator_list", []):
            reason = _is_unconditional_skip_marker(decorator)
            if reason:
                findings.append(
                    (path, decorator.lineno, f"{node.name} is disabled by {reason}")
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
                    )
                )

    return findings


def _key(path: Path, message: str) -> str:
    """Identity of a finding, deliberately excluding the line number.

    Editing a file above a known skip must not look like a new one.
    """
    test_name = message.split(" ", 1)[0]
    return f"{path.as_posix()}::{test_name}"


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

    current = {_key(p, m) for p, _, m in findings}

    if write_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(
            "# Known self-skipping tests, recorded at Phase 0.\n"
            "# This list may shrink, never grow. A new entry fails CI.\n"
            "# Remove a line by making the test assert or deleting it.\n"
            + "\n".join(sorted(current))
            + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(current)} entries to {baseline_path}")
        return 0

    baseline = _load_baseline(baseline_path)
    new = current - baseline

    if new:
        for path, line, message in findings:
            if _key(path, message) in new:
                print(f"{path}:{line}: {message}", file=sys.stderr)
        print(
            f"\n{len(new)} NEW self-skipping test(s). The baseline in "
            f"{baseline_path} may shrink, never grow.",
            file=sys.stderr,
        )
        return 1

    resolved = baseline - current
    if resolved:
        print(f"{len(resolved)} baselined skip(s) resolved — remove from baseline:")
        for entry in sorted(resolved):
            print(f"  {entry}")

    print(f"no new self-skipping tests ({len(current)} baselined)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
