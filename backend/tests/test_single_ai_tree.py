"""There must be exactly ONE AI package, and every entrypoint must resolve to it.

Why this file exists
--------------------
`backend/AI/` was a 94-file copy of the repo-root `AI/` package. 90 of its blobs
were byte-identical to the original; 4 had silently diverged, and every one of
those 4 had diverged in the direction of LESS safety:

  * `evaluation/groq_evaluator.py` -- the root copy refuses at construction
    unless GROQ_ALLOW_LLM_MARKING=true, because it lifts `score_awarded`
    straight out of an LLM reply and so cannot satisfy master spec rule 3. The
    shadow copy had NO such guard: `LLMMarkingDisabled` appeared zero times in
    the entire shadow tree.
  * `ocr/ocr_router.py` -- the shadow still wired Baidu Unlimited-OCR as
    primary #1, the engine that tokenizes the file PATH rather than the image
    and hardcodes confidence=0.92.
  * `ocr/providers/gemini_vision.py` -- same pin value, but with the 8-line
    comment recording the f5d7e7c revert incident stripped out.
  * `ocr/baidu_unlimited_engine.py` -- likewise stripped.

Which copy won was decided by import order and working directory, not by
design. The container sets PYTHONPATH=/app but WORKDIR=/app/backend, so a bare
`import AI.x` reaches /app/backend/AI FIRST and is only reordered by the
sys.path.insert at the top of backend/app/main.py. Any entrypoint that does not
route through main.py -- a worker, a management command, a REPL, a test run
from the wrong directory -- would have imported the unguarded LLM-marking path
and graded with it, silently.

These tests are the thing that stops the copy coming back.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

# AI/ has no __init__.py, so it is a NAMESPACE package. That matters here more
# than it looks: a namespace package does not let one directory shadow another,
# it MERGES them into a single __path__. Measured on the parent commit, from
# backend/:
#
#     AI.__path__ == ['D:\\GradeMIND\\backend\\AI', 'D:\\GradeMIND\\AI']
#
# Both trees were live inside one package, with the shadow FIRST, so
# AI.evaluation.groq_evaluator came from the copy with no kill switch while
# AI.evaluation.embeddings came from the real one. Nothing about that is
# visible at an import site. Because __file__ is None for a namespace package,
# the probe reports __path__ and the resolved file of a concrete submodule.
_PROBE = (
    "import AI, AI.evaluation.groq_evaluator as g, pathlib, json;"
    "print(json.dumps({"
    "'path': sorted({str(pathlib.Path(p).resolve()) for p in AI.__path__}),"
    "'groq': str(pathlib.Path(g.__file__).resolve())}))"
)


def _run_probe(cwd: Path, code: str) -> str:
    """Run `code` in a subprocess with cwd=`cwd`, PYTHONPATH=repo root.

    PYTHONPATH mirrors the container (ENV PYTHONPATH /app) so this reproduces
    the real resolution order rather than a convenient one. It must be a
    subprocess: the failure mode is interpreter start-up state (cwd landing on
    sys.path ahead of PYTHONPATH), which an in-process import cannot show.
    """
    import os

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        timeout=180,
        # Explicit DEVNULL, not inherited: under pytest's capture plugin on
        # Windows the inherited stdin handle is not duplicable and Popen dies
        # with OSError WinError 6 before the probe ever runs.
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, f"probe failed from {cwd}:\n{result.stderr}"
    return result.stdout


def _resolve_ai_from(cwd: Path) -> tuple[list[Path], Path]:
    """Return (unique dirs in AI.__path__, resolved groq_evaluator file)."""
    import json

    out = _run_probe(cwd, _PROBE)
    payload = json.loads(out.strip().splitlines()[-1])
    return [Path(p) for p in payload["path"]], Path(payload["groq"])


def test_no_duplicate_ai_tree_on_disk() -> None:
    """backend/AI/ must not exist. This is the root cause, not a symptom."""
    shadow = BACKEND_DIR / "AI"
    assert not shadow.exists(), (
        f"{shadow} exists again. A second copy of the scoring engine is not a "
        "convenience: the previous one dropped the GroqEvaluator kill switch "
        "and re-enabled a disabled OCR engine. Import from the repo-root AI/ "
        "package instead of copying it."
    )


def test_import_resolves_identically_from_root_and_backend() -> None:
    """`import AI` must reach the same file whether run from / or from backend/.

    This is the assertion the user asked for, and it is a subprocess test on
    purpose: the failure mode is entirely about interpreter start-up state
    (cwd on sys.path ahead of PYTHONPATH), which cannot be reproduced by
    importing inside an already-running pytest process.
    """
    root_dirs, root_groq = _resolve_ai_from(REPO_ROOT)
    backend_dirs, backend_groq = _resolve_ai_from(BACKEND_DIR)

    assert root_groq == backend_groq, (
        "AI.evaluation.groq_evaluator resolves to a different file depending on "
        "working directory:\n"
        f"  from {REPO_ROOT}: {root_groq}\n"
        f"  from {BACKEND_DIR}: {backend_groq}\n"
        "Two scoring engines are live and which one marks a script depends on "
        "where the process happened to be started."
    )

    expected = REPO_ROOT / "AI"
    for label, dirs in (("repo root", root_dirs), ("backend", backend_dirs)):
        assert dirs == [expected], (
            f"AI.__path__ from {label} is {dirs}, expected exactly [{expected}].\n"
            "AI/ is a namespace package, so extra entries are MERGED into one "
            "package rather than shadowed. Every directory listed here is live."
        )


@pytest.mark.parametrize("cwd", [REPO_ROOT, BACKEND_DIR], ids=["repo_root", "backend"])
def test_groq_kill_switch_present_wherever_ai_resolves(cwd: Path) -> None:
    """The resolved GroqEvaluator must refuse to construct by default.

    Asserted against whichever copy actually resolves, from both directories,
    so this fails if a shadow tree reappears carrying the unguarded variant --
    even if that tree is otherwise invisible to the path checks above.
    """
    import json

    probe = (
        "import os, json, AI.evaluation.groq_evaluator as g\n"
        "os.environ.pop('GROQ_ALLOW_LLM_MARKING', None)\n"
        "try:\n"
        "    g.GroqEvaluator()\n"
        "    r = 'CONSTRUCTED'\n"
        "except Exception as e:\n"
        "    r = type(e).__name__\n"
        "print(json.dumps({'has': hasattr(g, 'LLMMarkingDisabled'), 'result': r}))\n"
    )
    payload = json.loads(_run_probe(cwd, probe).strip().splitlines()[-1])

    assert payload["has"] is True, (
        f"the AI package reachable from {cwd} has no LLMMarkingDisabled symbol. "
        "That is the signature of the stripped shadow copy: the deleted "
        "backend/AI/ tree contained zero occurrences of it."
    )
    assert payload["result"] == "LLMMarkingDisabled", (
        f"GroqEvaluator constructed successfully from {cwd} "
        f"(got {payload['result']}). It must refuse unless "
        "GROQ_ALLOW_LLM_MARKING=true: it takes the mark from an LLM reply and "
        "cannot satisfy master spec rule 3."
    )
