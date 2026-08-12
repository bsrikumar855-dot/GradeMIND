# GradeMIND — Baseline Audit

**Date:** 2026-08-12
**Auditor:** Claude Code (read-only pass; no files modified, no commits, no pushes during audit)
**Base audited:** `2e12467` (`Merge pull request #12`) — the tip of `origin/post-round2-dev`
**Reference base in spec:** `d799b0f` (`origin/main`, `origin/release/ai-platform-v1`)
**Diff:** `post-round2-dev` vs `d799b0f` — 730 files changed, +7,383 / −58,109

Scope per instruction: D1/D2/D3/D6/D10 accepted as pre-verified and not re-derived. Everything
else verified against working-tree code. New findings from the 730-file delta are recorded in §3.

---

## 1. Local checkout state

The local working copy is on a branch named `release/ai-platform-v1`, but its tip is `2e12467` —
identical to `origin/post-round2-dev`. The local branch name shadows a remote branch of the same
name that is still at `d799b0f`.

```
* release/ai-platform-v1   2e12467 [origin/release/ai-platform-v1: ahead 12]
  post-round2-dev          2e12467 [origin/main: ahead 12]
  remotes/origin/release/ai-platform-v1   d799b0f
  remotes/origin/post-round2-dev          2e12467
```

**Content is correct; only the label is misleading.** Phase branches are cut from `2e12467`.

> **Hazard:** pushing local `release/ai-platform-v1` would move the remote branch of that name
> 12 commits forward. Do not push that branch. Phase work goes on `prod/phase-*` branches only.

---

## 2. Defect table — verified

Legend: **PRESENT** = confirmed in working tree · **FIXED** = confirmed absent ·
**PARTIAL** = partially remediated · **(pre-verified)** = accepted from your remote check, not re-derived.

| ID | Status | Evidence |
|----|--------|----------|
| D1 RCE | FIXED (pre-verified) | Re-swept anyway: `frontend/src/app/api/` **does not exist**; no `child_process` / `exec(` / `eval(` / `spawn(` / `rmSync` anywhere under `frontend/src/`. See §3 N7 on what this means for Gate 0(a). |
| D2 auth bypass | FIXED (pre-verified) | `config.py:23` `AUTH_ENABLED: bool = True`; `config.py:15` `SECRET_KEY: str` (no default). See N8 — the Phase 0.6 hardening is *not* yet implemented. |
| D3 student data in history | **PARTIAL — and materially misdescribed.** | See §3 N1. Tree is clean (`.gitkeep` only). History still exposes student PII, but **not** 99 PDFs. |
| D4 requirements | **PARTIAL** | `numpy`, `opencv-python-headless`, `google-generativeai`, `pytest-cov` present. Still undeclared: `sentence-transformers` (`AI/evaluation/embeddings.py:33,44`), `reportlab` (`AI/reports/report_data_builder.py:940`), `paddleocr` (`AI/ocr/paddle_engine.py:21`, `AI/paddle_ocr_reader.py:34`). `paddleocr`/`easyocr`/`torch`/`transformers` are declared in `requirements-ocr.txt` (optional profile) — `sentence-transformers` and `reportlab` are in **neither** file. Also: every dep is `>=`-pinned, none exact; no `requirements/` split; no lockfile. |
| D5 name-based authz | **PRESENT — broader than stated** | `student_service.py:124`. Two further name-keyed paths found; see N4. |
| D6 no CI | FIXED, but shallow | `.github/workflows/tests.yml` exists and **does** gate. See N6 for what it does not cover. |
| D7 verification thresholds | **PRESENT** | `AI/evaluation/verification_engine.py:45` `score_diff > 2.0`, `:48` `elif score_diff > 0.5`, `:51` `elif conf_diff > 0.30`. Absolute marks, unnormalized; `conf_diff` unreachable whenever `score_diff > 0.5`. |
| D8 heuristics | **PRESENT** | `autonomous_evaluator.py:101` `_factual_error_penalty` in scoring path; photosynthesis branches at `:201`, `:203`, `:210`. |
| D9 depth-as-marks | **PRESENT** | `autonomous_evaluator.py:100` `_depth_alignment` feeds `rubric_alignment`; definition at `:256`. |
| D10 build cache | FIXED in tree (pre-verified) | Still in history — see N1. |
| D11 CORS regex | **PRESENT** | `config.py:30` `CORS_ALLOWED_ORIGIN_REGEX = r"https://.*\.vercel\.app"`, applied at `main.py:79` alongside `allow_credentials=True` (`main.py:80`). |
| D12 upload buffering | **PRESENT — 3 sites, not 1** | `submissions.py:122` `await file.read()` → validated at `:127`. `uploads.py:51` → validated `:52`. `uploads.py:92` → validated `:93`. Every path buffers the whole body before the size check. |

---

## 3. New findings

### N1 — D3 is misdescribed; the real exposure is different and the purge scope is wider

Full-history object inventory under `backend/storage/`: **474 distinct paths**, by extension:

```
102 .json
  2 .gitkeep
  1 .png
  1 .pdf
```

A whole-history sweep for `*.pdf` **anywhere** in the repo returns exactly one blob
(`backend/storage/answer_sheets/003340e0-.../CS005_fe7deca0.pdf`). **There are not 99 PDFs in this
repository's history.** Either they were never committed, or they live in a repo/remote this clone
does not have.

That does not make the purge optional. The 102 JSON blobs are the real exposure —
`backend/storage/reports/*.json` carry identity fields directly:

```json
{ "submission_id": "3c1e31a4-…", "student_name": "Status Test",
  "student_roll_number": "CS005", "exam_id": "003340e0-…", … }
```

and `backend/storage/ocr_outputs/*.json` carry extracted answer text with bounding boxes. Names +
roll numbers + answer content is precisely the DPDP-relevant set. **Purge still required** — the
justification is the JSON, not the PDFs.

**Separately, and larger:** the dominant history objects are not in the spec's purge list at all.

```
1455404037  tmp/backend-server.err.log
1455049569  tmp/backend-server.err.log
1045189169  tmp/backend-server.err.log
  62114076  frontend/.next-prod/cache/webpack/client-production/0.pack
  61966154  frontend/.next-prod/cache/webpack/client-production/0.pack
   …
```

**~3.95 GB of uvicorn dev-server logs across three blobs.** They pack down small (`.git` is 82 MB)
because the files are mostly whitespace padding, but they are in history and they are the reason
`.git` will not reach the Gate 0(e) `< 50 MB` target from a `.next-prod`-only purge.

I scanned the first 40 MB of the largest blob for credential patterns — `SECRET_KEY`,
`DATABASE_URL`, `postgresql://`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `AIza`, `Bearer `, `password`,
`Authorization` — **zero hits**. Content is uvicorn request lines (`[INFO] GET /dashboard/overview
403 81ms`). Not a credential incident on the evidence sampled; still 3.95 GB of junk that must go.

> **Spec amendment required:** Phase 0.3's `git filter-repo` scope must add `tmp/**`. Purging only
> `backend/storage/**`, `frontend/.next-prod/**`, `frontend_backup/**` leaves the largest objects
> in place and will miss Gate 0(e).

### N2 — `.gitignore` is `backend/`-anchored; the app's test tooling writes to repo root

`.gitignore` ignores `backend/storage/*` and `backend/e2e_results.json`. But
`backend/e2e_qa_test.py:166` uses a **relative** path:

```python
test_file_path = Path("storage/test_answer_sheet.png")
```

Run from the repo root — as it evidently was — this writes `./storage/` and `./e2e_results.json`,
neither of which any ignore rule matches. This is the exact mechanism that produced two of the three
currently-staged files (§5). `storage_service.STORAGE_ROOT` itself is correct
(`config.BASE_DIR` resolves to `backend/`, so real uploads land in `backend/storage/`) — the leak is
from ad-hoc test tooling only.

Phase 0.5 proposes adding `backend/storage/` to `.gitignore`; that rule **already exists**. The
missing rules are root-level `/storage/` and `/e2e_results.json`.

### N3 — `scratch_fix_db.py` is a live migration-state destroyer

`backend/scratch_fix_db.py` (Phase 0.10 already schedules deletion — recording severity):

```python
engine = create_engine(settings.DATABASE_URL)
conn.execute(text("DROP TABLE IF EXISTS alembic_version;"))
```

No environment guard. It drops Alembic state against whatever `DATABASE_URL` is configured,
production included. `backend/e2e_qa_test.py` also still present.

### N4 — D5 is not a one-line fix

Beyond `student_service.py:124`, two further name-keyed paths:

- `student_service.py:66` — `get_student_results_overview()` queries
  `Submission.student_name.ilike(student_name)`. A second, independent cross-student leak: `ilike`
  is case-insensitive **and** the caller-supplied string is unescaped, so `%` in a name matches
  broadly.
- `student_service.py:96` — the response sets `"student_id": student_name`. The API surfaces a
  display name in a field consumers will treat as a stable identifier.
- `student_service.py:116` — `user_name = current_user.get("name")`; if absent, `:124`'s
  `user_name.lower()` raises `AttributeError` → 500. Confirmed as originally described.

Phase 1.1's rewrite must cover all three, and the `student_id` field rename is a breaking API change
— flag its blast radius in the Phase 1 PR.

### N5 — `EmbeddingService` silently substitutes a different model

`AI/evaluation/embeddings.py:32-53`: on **any** `Exception` loading the preferred model, it logs a
warning and loads `fallback_model_name` instead. Only if the fallback also fails does it raise.

A silent model swap changes every semantic similarity score. The same answer can receive different
marks across runs depending on which model happened to load — directly contradicting Phase 2.6
(`embedding_model` recorded, byte-for-byte reproducible) and Standing Constraint "no silent fallbacks
in the scoring path". The final `raise RuntimeError` is correct behaviour; the fallback above it is
not.

Fix in Phase 2: record the resolved model name on the evaluation record and make substitution
either explicit-and-versioned or fatal.

### N6 — CI gates, but shallowly

`.github/workflows/tests.yml` runs `pytest` for `backend/tests/` and `AI/tests/` on push and PR.
A test failure fails the step and the job — **it is not vacuous**. Gaps:

- No `--cov-fail-under`. Coverage is reported (`--cov-report=term-missing`) on three services only,
  and enforced nowhere.
- No lint (`ruff`), no type-check (`mypy --strict` on `AI/`), no container build, no image scan.
- Installs `requirements.txt` only, by design. Combined with D4, `sentence-transformers` and
  `reportlab` are absent in CI — so the semantic-engine and report tests **skip rather than run**.
  Skip markers found in 5 of 16 `AI/tests/` files (`test_ocr_benchmark.py`, `test_ocr_pipeline_cli.py`,
  `test_semantic_engine.py`, `test_or_question_resolver.py`, and one more).
- Whether it is a **required** status check on the remote could not be determined locally. Worth
  confirming in the GitHub branch-protection settings — an unrequired check gates nothing.

`AI/tests/test_or_question_resolver.py:321` calls `pytest.skip()` inside a test body on an assertion
that did not hold ("acceptable for OCR noise case"). That is a failing case converted into a skip.

### N7 — Gate 0(a) is now a tautology

`frontend/src/app/api/` does not exist; the frontend calls the backend directly. The gate's grep
will pass unconditionally, including if someone adds a route with `child_process` tomorrow (the grep
targets a path that isn't there). The pre-commit hook from Phase 0.2 is the control that actually
does work here — the gate command should be widened to `frontend/src/**`.

### N8 — Phase 0.6 hardening is unimplemented

`AUTH_ENABLED` defaults `True` (D2 fixed), but the Phase 0.6 requirement — bypass permitted **only**
when `AUTH_ENABLED=False` **and** `DEBUG=True` **and** `ENVIRONMENT=local`, else `Settings` raises at
import — is not built. There is **no `ENVIRONMENT` setting** anywhere in `backend/app/` or
`docker-compose.yml`; it must be added. No `MVP_ANONYMOUS_USER_ID` in config (already gone);
`get_current_user` lives at `backend/app/api/auth_deps.py:37`, not in `core/`.

---

## 4. Golden set — confirmed absent

No `golden`, `ground_truth`, or `marking_scheme` fixtures on any branch. **Assist-only is adopted as
the shipping target**, per your §4, not as a post-Phase-3 fallback:

- Phase 3 gate → HTR provider interface exists, is swappable, propagates per-line confidence. **No
  accuracy claim, no CER figure.**
- Phase 2 → value-point engine built in full (data-independent); semantic thresholds ship as
  documented, uncalibrated defaults, flagged as such in code and config.
- Phase 6 gate → QWK harness exists and runs in CI, dark until a labelled set lands.
- Lane assignment → **`AUTO` disabled at config level.** Every question routes `REVIEW` or
  `MANDATORY_HUMAN`.

---

## 5. Uncommitted working-tree state

Three files staged, none committed by this audit:

| File | Assessment |
|------|------------|
| `e2e_results.json` (146 lines) | Output of `backend/e2e_qa_test.py`, written to repo root (N2). Records `"passed": 12, "failed": 11, "total": 23, "score_pct": 52.2` with 11 named failures (422s on exam create/update, submission upload). **Should not be committed** — it is a build artifact, and the tool that generates it is slated for deletion in Phase 0.10. The failures themselves are worth reading: they suggest the exam/submission API contract is broken against its own E2E script. |
| `storage/test_answer_sheet.png` (69 bytes) | Stub fixture from the same script (N2). Not student data at 69 bytes. **Should not be committed**; root `/storage/` should be gitignored. |
| `frontend/src/app/(authenticated)/analytics/page.tsx` (307 lines) | Real frontend work, unrelated to Phase 0. Outside declared Phase 0 scope — per operating rule 6 I have not touched it. **Your call:** commit separately on a feature branch, or carry into the Phase 5 UI rewrite. |

All three remain staged and unmodified. The Phase 0 branch commit uses an explicit pathspec so none
of them are swept in.

---

## 6. Revised Phase 0 scope

Dropped (verified complete): D1, D2 (default only — see N8), D10 tree cleanup.

| # | Item | Source |
|---|------|--------|
| 0.1 | Complete D4: declare `sentence-transformers` + `reportlab`; split `requirements/{base,ai,dev}.txt`; pin exact versions; generate lockfile | D4 |
| 0.2 | D11: drop the `.vercel.app` regex, explicit env allowlist | D11 |
| 0.3 | D12: stream-and-reject before buffering, all **3** sites | D12 |
| 0.4 | `.githooks/pre-commit` + `core.hooksPath` | Phase 0.2 |
| 0.5 | `.gitignore`: root `/storage/`, `/e2e_results.json`, `tmp/`, `*.pack`, `*.pack.old` | N1, N2 |
| 0.6 | Implement the `AUTH_ENABLED`/`DEBUG`/`ENVIRONMENT=local` triple-gate; add `ENVIRONMENT` setting | N8 |
| 0.7 | Delete `backend/scratch_fix_db.py`, `backend/e2e_qa_test.py` | N3 |
| 0.8 | `docs/CREDENTIAL_ROTATION.md` (human checklist, no rotation performed by me) | Phase 0.4 |
| 0.9 | `docs/HISTORY_REWRITE.md` — **scope amended to include `tmp/**`** — then ask before force-push | Phase 0.3, N1 |
| 0.10 | Widen Gate 0(a) grep to `frontend/src/**` | N7 |

Deferred to Phase 1 (recorded here, not fixed in Phase 0): D5/N4, D7, D8, D9, N5, N6.

**Blast radius if Phase 0 is wrong:** 0.1/0.6 can prevent the backend from starting (config raises at
import, or a dep resolves wrong). 0.2 can break the deployed frontend's ability to call the API. 0.3
touches the upload path — a bug there rejects valid submissions. 0.9 rewrites shared history and is
gated on explicit approval.

---

## 7. Not verified

Stated plainly rather than assumed:

- **Test suite not executed.** No pass/fail count is claimed here. The `a6a1107` message reports
  "120 passed, 0 failed" as of 2026-07-21; that is quoted, not reproduced.
- **`docker compose build` not run.** The D4 claim that the container dies on
  `sentence-transformers`/`reportlab` is inferred from import sites vs. declared deps, not from a
  build. Gate 0(b) will settle it.
- **Branch protection / required-check status on the remote** — not inspectable locally (N6).
- **Credential exposure beyond the first 40 MB** of the largest log blob (N1). The remaining
  ~1.4 GB of that blob, and the two other log blobs, were not scanned.
