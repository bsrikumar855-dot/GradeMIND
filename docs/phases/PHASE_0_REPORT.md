# Phase 0 — Containment: Report

**Branch:** `prod/phase-0-containment`
**Base:** `2e12467` (tip of `origin/post-round2-dev`)
**Commits:** `5aafa6e` (audit) · `8773feb` (audit correction) · `da1b32c` (Phase 0)
**Status:** items 1.1–1.8 complete. Item 1.9 (history rewrite) documented, **not executed**, awaiting approval.

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
| 0(b) container builds + imports every module | CI-VERIFIED | pending run |
| 0(c) embedding service raises on unloadable model | CI-VERIFIED | pending run |
| 0(d) pre-commit hook blocks | LOCALLY-VERIFIED | PASS (5 rules) |
| 0(e) upload cap without buffering | **PARTIAL** — unit-level LOCALLY-VERIFIED; RSS/disk probe CI-VERIFIED | see §3 |
| 0(f) CI green on clean clone | CI-VERIFIED | pending run |
| ruff | LOCALLY-VERIFIED | PASS (scoped — §3) |
| mypy | LOCALLY-VERIFIED | PASS (scoped — §3) |
| compose duplicate-key lint | LOCALLY-VERIFIED | PASS |
| self-skipping-test ratchet | LOCALLY-VERIFIED | PASS |
| backend test suite | **NOT RE-RUN after final edits** | see §4 |

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

## 4. Test suite — stated precisely

The last **full** backend run was before the final edits:

```
1 failed, 120 passed, 4 warnings in 174.98s
FAILED tests/test_submissions.py::TestFileValidation::test_reject_oversized_file
  assert 413 == 400
```

That failure *was* the D12 fix working — the cap now returns 413, which is the
correct status. The assertion was updated, and the affected file re-run:

```
$ pytest backend/tests/test_submissions.py -q     # after the 413 fix
19 passed
```

**The full suite has not been re-run since the log-redaction and body-limit
work landed.** Targeted files pass (§2). CI job `test` settles it. Do not read
"120 passed" as a current number.

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
| `ENVIRONMENT` triple-gate | Audit item 0.6 — `AUTH_ENABLED` defaults `True`, but the `AUTH_ENABLED=False` + `DEBUG=True` + `ENVIRONMENT=local` requirement is **not built**; no `ENVIRONMENT` setting exists. **Outstanding.** |

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
