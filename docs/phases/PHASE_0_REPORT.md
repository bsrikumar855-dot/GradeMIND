# Phase 0 — Containment: Report

**Branch:** `prod/phase-0-containment`
**Base:** `2e12467` (tip of `origin/post-round2-dev`)
**Commits:** `5aafa6e` (audit) · `8773feb` (audit correction) · `da1b32c` (Phase 0) ·
`d429465` (report) · `e147c18` (CLAUDE.md) · **A1** (this update)
**Status:** items 1.1–1.8 complete, **A1 complete**. Item 1.9 (history rewrite) documented,
**not executed**, gated on a per-session approval line.

> **Sequencing changed:** A1 → A2 → **A4** → A3. A4 rewrites every commit hash, so it runs while
> exactly one branch exists rather than after Track B and Track C spawn five more. See `CLAUDE.md`.

---

## Verification tiers

Two tiers, kept deliberately separate. Nothing below is described as "passed"
without saying which tier it sits in.

| Tier | Meaning |
|---|---|
| **LOCALLY-VERIFIED** | Run on this machine, raw output pasted in §2 |
| **CI-VERIFIED** | Requires Docker or a clean runner; written as a CI step, awaiting a run URL |
| **NOT RUN** | Neither. Stated with the reason. |

This machine has no Docker daemon, no `gh`, and no `pip` outside `backend/venv`:

```
docker   NOT FOUND        (daemon NOT reachable)
gh       NOT FOUND
python   Python 3.14.2    (backend/venv: fastapi 0.136.3, pytest 9.0.3, ruff 0.16.2, mypy 2.3.0)
```

So Gate 0 (b), (c), (e), (f) cannot produce local output and are CI-VERIFIED
by construction. Their run URL must be pasted here before Phase 0 is called
done.

---

## 1. Gate status

| Gate | Tier | Result |
|---|---|---|
| 0(a) no shell-exec surface in `frontend/src/**` | LOCALLY-VERIFIED | PASS |
| 0(b) container builds + imports every module | CI-VERIFIED | **pending run — no URL yet** |
| 0(c) embedding service raises on unloadable model | CI-VERIFIED | **pending run — no URL yet** |
| 0(d) pre-commit hook blocks | LOCALLY-VERIFIED | PASS (5 rules) |
| 0(e) upload cap without buffering | **PARTIAL** — control unit-tested LOCALLY-VERIFIED; probe written, NOT RUN | §3, §2 |
| 0(f) CI green on clean clone | CI-VERIFIED | **pending run — no URL yet** |
| `ENVIRONMENT` triple-gate (A1) | LOCALLY-VERIFIED | PASS — 27/27, exhaustive matrix |
| ruff | LOCALLY-VERIFIED | PASS (scoped — §3) |
| mypy | LOCALLY-VERIFIED | PASS (scoped — §3) |
| compose duplicate-key lint | LOCALLY-VERIFIED | PASS |
| self-skipping-test ratchet | LOCALLY-VERIFIED | PASS |
| backend test suite | LOCALLY-VERIFIED | **164 passed, 0 failed** |
| AI test suite | LOCALLY-VERIFIED | **167 passed, 6 skipped (baselined)** |

---

## 2. Raw output — LOCALLY-VERIFIED only

### Gate 0(a)

```
$ grep -rnE "child_process|execAsync|[^a-zA-Z_.]exec\(|[^a-zA-Z_.]spawn\(|[^a-zA-Z_.]eval\(" frontend/src/
grep exit=1 (1 = no matches = PASS)
```

Widened from `frontend/src/app/api/` — that directory no longer exists, so the
original gate passed vacuously and would not have noticed the route being
reintroduced elsewhere.

### Gate 0(d) — pre-commit hook

```
$ echo "const {exec} = require('child_process')" > frontend/src/probe.ts && git add -f frontend/src/probe.ts
$ git commit -m "probe: should be blocked" -- frontend/src/probe.ts
pre-commit: shell-exec surface in frontend/src/probe.ts
1:const {exec} = require('child_process')

pre-commit: commit rejected. Fix the above, or use --no-verify only if you can say why.
COMMIT_EXIT=1 (non-zero = PASS)
```

All five rules:

```
=== 5MB rule ===        exit=1 (want 1)
=== .env rule ===       exit=1 (want 1)
=== .pem rule ===       exit=1 (want 1)
=== .env.example allowed ===  exit=0 (0 = allowed = PASS)
```

Duplicate-key rule, driven with the exact `a6a1107` regression reintroduced:

```
$ python scripts/check_compose_duplicate_keys.py docker-compose.yml
docker-compose.yml:37: duplicate key 'AUTH_ENABLED' in services.backend.environment — YAML keeps the last occurrence, so the earlier value is silently discarded
docker-compose.yml:38: duplicate key 'AUTH_ENABLED' in services.backend.environment — YAML keeps the last occurrence, so the earlier value is silently discarded
CHECKER_EXIT=1 (want 1)

$ git commit -m "probe: dup key" -- docker-compose.yml
pre-commit: duplicate environment keys in docker-compose.yml: AUTH_ENABLED
pre-commit: commit rejected.
HOOK_EXIT=1
```

`docker-compose.yml` restored; `git diff --stat` clean afterwards.

### Lint and policy gates

```
$ ruff check backend/app AI scripts
All checks passed!

$ mypy AI/evaluation/embeddings.py
Success: no issues found in 1 source file

$ python scripts/check_compose_duplicate_keys.py docker-compose.yml
docker-compose.yml: no duplicate keys

$ python scripts/check_no_self_skipping_tests.py
no new self-skipping tests (7 baselined)
```

### Body limit unit tests

```
$ pytest backend/tests/test_body_limit.py -q
......                                                                   [100%]
6 passed in 0.06s
```

### PII redaction tests

```
$ pytest backend/tests/test_log_redaction.py -q
..........                                                               [100%]
10 passed in 0.10s
```

### A1 item 1 — `ENVIRONMENT` triple-gate

```
$ pytest backend/tests/test_environment_gate.py -q
...........................                                              [100%]
27 passed in 0.11s
```

Exhaustive: all 16 combinations of `AUTH_ENABLED` × `DEBUG` × `ENVIRONMENT`,
plus a test that *counts* the accepted bypass combinations and asserts there is
exactly one — so loosening `and` to `or` fails even if someone updates the
expectation helper to match.

The gate fires at `Settings` construction, i.e. import time. Verified
incidentally and forcefully: this machine's `backend/.env` carries
`AUTH_ENABLED=false` with `DEBUG=True` and no `ENVIRONMENT`, and the backend
now **refuses to start**:

```
app.core.config.AuthBypassNotPermitted: AUTH_ENABLED=False is only permitted for
local development, and requires DEBUG=True and ENVIRONMENT=local at the same time.
Unmet: ENVIRONMENT="local". (ENVIRONMENT=production, DEBUG=True).
```

That is the gate working as designed, and it is an action item — see §9.

`MVP_ANONYMOUS_USER_ID` is removed. Its replacement, `get_local_dev_user()`,
generates a per-process UUID rather than a fixed sentinel, so audit rows from
different local runs are distinguishable.

### A1 item 2 — Gate 0(e) probe

`scripts/probe_upload_limit.py` written. **Not yet run** — it needs a live
server, so it is CI-VERIFIED work pending A2.

It asserts **peak temp-disk footprint as well as peak RSS**, on an interval
sampler, because an RSS-only assertion certifies the wrong thing: Starlette's
`max_part_size` check sits under `if self._current_part.file is None:` and so
does not bound *file* parts, which spill to an uncapped `SpooledTemporaryFile`.
An implementation that streams 2 GB to disk keeps RSS flat and passes an
RSS-only gate.

Three cases: `honest` Content-Length, `understated` Content-Length (header
check passes, counter must catch it), and `chunked` with no Content-Length at
all (header check never fires).

It also warns if the temp filesystem has less free space than the probe size —
otherwise a buffering implementation could hit `ENOSPC` before the assertion
fires, which would read as a pass.

### De-skipped OR test

```
$ pytest AI/tests/test_or_question_resolver.py -q
...............................                                          [100%]
31 passed in 0.17s
```

### Middleware order

```
middleware (outermost first): ['CORSMiddleware', 'BodySizeLimitMiddleware', 'LoggingMiddleware', 'JWTAuthMiddleware']
```

CORS outermost so a 413 still carries CORS headers and a browser client can
read the error rather than seeing an opaque network failure.

---

## 3. Where the delivered work is narrower than the gate as written

Stated here rather than blurred into a pass.

### Gate 0(e) is partially satisfied

The probe as specified — `scripts.probe_upload_limit --size 2GB --expect 413
--assert-peak-rss-under 256MB` — is **not written**, because it needs a running
server. What exists is unit-level proof of the control itself
(`test_body_limit.py`), including the two cases a header check misses: a
chunked body with no `Content-Length`, and an understated `Content-Length`.

**The RSS assertion alone certifies the wrong thing.** Starlette writes file
parts to a `SpooledTemporaryFile`, which spills to *disk* past 1 MB. A
disk-spooling implementation passes an RSS-only assertion while writing 2 GB to
the system temp directory. When the probe is written it must assert **peak disk
as well as peak RSS**.

### The outermost body cap is not in this repo

Whatever fronts the app in production — nginx `client_max_body_size`, or the
platform's own request cap — is the first line and should be set at or below
the app's 20 MB. Not ours to set here; flagged so it does not fall between
owners.

### ruff and mypy gates are scoped, not absolute

Ruff's default rules report **1065** findings; `mypy --strict AI/` cannot
resolve the package at all. Gating on either as written means Phase 0 can never
go green, and clearing them means editing several hundred files outside this
phase's declared scope.

Enforced now: ruff `E9`/`F821`/`F811`/`F5xx` (defects, not style), and mypy
per-module on what Phase 0 rewrote. Both ratchet, with the backlog and reason
recorded in `pyproject.toml`. The standing `--strict` target is unchanged; it
is scheduled, not abandoned.

Five real `F821` undefined-names were found and fixed on the way: a missing
`Tuple` import in `gap_detector.py`, and `np`/`Image` annotations in
`trocr_engine.py`.

### No lockfile

`requirements/*.txt` pin every direct dependency exactly, but no lockfile is
generated. A lock resolved on Windows/Python 3.14 would be wrong for the
Linux/3.12 container. It must be generated in CI or on a Linux host —
`pip-compile --generate-hashes` per file. **Outstanding.**

---

## 4. Test suite — current

**LOCALLY-VERIFIED.** Full backend suite, re-run after all Phase 0 and A1 edits:

```
$ PYTHONPATH=. DATABASE_URL="sqlite:///./ci_test.db" SECRET_KEY="ci-test-secret-key" \
  AUTH_ENABLED="True" ENVIRONMENT="ci" pytest backend/tests/ -q
........................................................................ [ 43%]
........................................................................ [ 87%]
........................                                                 [100%]
164 passed, 4 warnings in 164.03s (0:02:44)
```

AI suite:

```
$ PYTHONPATH=. pytest AI/tests/ -q
167 passed, 6 skipped, 4 warnings in 62.70s (0:01:02)
```

**331 passed, 0 failed, 6 skipped.**

### Suppressed tests — two different numbers, do not conflate them

| | Count | What it is |
|---|---|---|
| Runtime skips | **6** | Optional-engine guards that fire when OpenCV / an OCR engine is absent. Legitimate. |
| **Baselined self-skipping tests** | **7** | Tests that decline to assert. `scripts/self_skipping_tests_baseline.txt`. |

The 7 baselined entries are **suppressed failures**, not passes, and
"331 passed, 0 failed" must not be read as absorbing them. The ratchet
(`scripts/check_no_self_skipping_tests.py`) stops new ones appearing — but a
ratchet with no burn-down owner is a permanent exemption with extra steps.

**Target: baseline count 0 by end of Track C.** It may shrink, never grow.

Current entries:

```
AI/tests/test_ocr_benchmark.py::test_content_type_classifier_printed
AI/tests/test_ocr_benchmark.py::test_preprocessing_pipeline_runs
AI/tests/test_ocr_pipeline_cli.py::test_adaptive_threshold_produces_binary_output
AI/tests/test_ocr_pipeline_cli.py::test_full_pipeline_real_engine_returns_nonempty_text
AI/tests/test_ocr_pipeline_cli.py::test_preprocess_for_engine_binarize_flag_changes_output
AI/tests/test_ocr_pipeline_cli.py::test_preprocess_for_engine_unknown_falls_back_to_tesseract_profile
AI/tests/test_semantic_engine.py::TestSemanticEngineIntegration
```

Six of the seven are OCR-engine dependent and land naturally in Phase 3, where
the engines become a declared dependency rather than an optional import. The
seventh, `TestSemanticEngineIntegration`, is disabled by
`@pytest.mark.skipif(True, ...)` — an unconditional off switch, not a
capability guard — and `requirements/ai.txt` now installs the dependency it was
waiting for. That one has no excuse left and should go first.

`test_or_question_resolver.py::test_ocr_noisy_or_still_resolves` was the eighth
and is already fixed: it called `pytest.skip("acceptable fallback")` in the
else-branch of an assertion, on a branch that was also dead. It now asserts.

The previously reported "120 passed / 1 failed" is superseded and must not be
carried forward. That single failure was the D12 fix working — the cap returns
413 where the old test expected 400 — and the assertion was corrected.

### Known warning, not fixed

```
AI/evaluation/embeddings.py:199: FutureWarning: The `get_sentence_embedding_dimension`
method has been renamed to `get_embedding_dimension`.
```

Deliberately left. `sentence-transformers` is pinned at `3.3.1` where the old
name still works; changing it now would silently break anyone on an older pin.
Fold into the Phase 2 work that touches this module.

---

## 5. Files changed

```
39 files changed, 2581 insertions(+), 701 deletions(-)
```

New: `backend/app/core/body_limit.py`, `backend/app/core/log_redaction.py`,
`backend/tests/test_body_limit.py`, `backend/tests/test_log_redaction.py`,
`requirements/{base,ai,htr,dev}.txt`, `pyproject.toml`, `.githooks/pre-commit`,
`scripts/check_compose_duplicate_keys.py`,
`scripts/check_no_self_skipping_tests.py`,
`scripts/self_skipping_tests_baseline.txt`, `docs/CREDENTIAL_ROTATION.md`,
`docs/HISTORY_REWRITE.md`, `docs/RUNBOOK_LOCAL_DEV.md`.

Deleted: `backend/scratch_fix_db.py` (unguarded `DROP TABLE alembic_version`
against the configured `DATABASE_URL`), `backend/e2e_qa_test.py`,
`backend/requirements.txt`, `backend/requirements-ocr.txt`.

Untouched and outside scope: `frontend/src/app/(authenticated)/analytics/page.tsx`
remains untracked, for a separate branch or the Phase 5 rewrite.
`e2e_results.json` and `storage/test_answer_sheet.png` are now gitignored and
were removed from the index without being committed.

---

## 6. Known gaps carried into Phase 1

| Item | Note |
|---|---|
| D5 name-based authz | Three sites (`student_service.py:66` unescaped `ilike`, `:96` returns `student_id = student_name`, `:124` name equality). Phase 1.1. |
| D7 verification thresholds | Absolute marks, unreachable `conf_diff` branch. Phase 4.3. |
| D8/D9 heuristics | `_factual_error_penalty`, `_depth_alignment`, photosynthesis branches still in the scoring path. Phase 2.5. |
| Lockfile | §3. |
| Gate 0(e) probe | §3 — must assert peak disk as well as peak RSS. |
| `mypy --strict` on all of `AI/` | Ratcheting from one module. |
| Upstream body cap | Not in this repo; needs an owner. |
| ~~`ENVIRONMENT` triple-gate~~ | **DONE in A1.** 27 tests, exhaustive matrix. |

---

## 7. Blast radius

- **1.1 / Dockerfile** — wrong pins or a missing dep stops the container building.
- **1.3 CORS** — an incomplete allowlist breaks the deployed frontend's ability to call the API.
- **1.4 uploads** — touches every upload path; a bug rejects valid submissions.
- **1.2 embeddings** — converts a previously silent degradation into a hard
  failure. Any environment quietly running on the fallback model now fails
  loudly. That is the intent, and it will look like a new outage.
- **1.9** — not executed. Rewrites shared history when it is.

---

## 8. Process note

During Gate 0(d) probing, an unconditional `git reset --soft HEAD~1` ran after
a commit the hook had *blocked*, so it dropped commit `8773feb` (the audit
correction) instead of the probe. Caught by an unexpected diff, diagnosed from
the reflog, and restored with `git reset --soft 8773feb`; the remote had never
lost it. No content lost. Recorded because a cleanup step that assumes its
preceding command succeeded is the same class of defect as the duplicate-key
merge this phase added a hook for.

---

## 9. Action item for the repository owner

**Your `backend/.env` will no longer start the backend.** It carries
`AUTH_ENABLED=false` and `DEBUG=True` with no `ENVIRONMENT`, which now defaults
to `production` — so the triple gate refuses to construct `Settings`.

This is the gate doing exactly what it was asked to do, and it is worth pausing
on: that file has been running with **authorization disabled and no
environment marker**, which means every request was served as an anonymous
ADMIN with nothing in the configuration recording that this was meant to be a
local-only state.

One line fixes it:

```
ENVIRONMENT=local
```

`backend/.env` is untracked and holds secrets, so it has not been edited here.

The same variable was added to `backend/.env.example`, `.env.example`, and
`docker-compose.yml` (defaulting to `production` in both non-local places).
