# GradeMIND — Baseline Audit

**Date:** 2026-08-12
**Revised:** 2026-08-12 — §3 N1 (git-history forensics) was wrong and has been replaced. See §0.
**Auditor:** Claude Code (read-only pass; no files modified, no commits, no pushes during audit)
**Base audited:** `2e12467` (`Merge pull request #12`) — the tip of `origin/post-round2-dev`
**Reference base in spec:** `d799b0f` (`origin/main`, `origin/release/ai-platform-v1`)
**Diff:** `post-round2-dev` vs `d799b0f` — 730 files changed, +7,383 / −58,109

Scope per instruction: D1/D2/D3/D6/D10 accepted as pre-verified and not re-derived. Everything
else verified against working-tree code. New findings from the 730-file delta are recorded in §3.

---

## 0. Correction notice — retracted finding

The first revision of this document claimed ~3.95 GB of `tmp/backend-server.err.log` blobs in git
history, an 82 MB `.git`, and a credential scan performed against those blobs. **That finding is
retracted.** Nothing under `tmp/` has ever been committed to this repository.

The command and its output were real and are reproducible, but they were **mis-scoped**, and the
conclusion drawn from them was wrong. Root cause, established by command:

```
$ git for-each-ref --format='%(refname) -> %(objecttype)' | grep '^refs/codex/' | head -3
refs/codex/turn-diffs/checkpoints/02d2140a…/f18f0654-… -> tree
refs/codex/turn-diffs/checkpoints/055f1e6c…/5bbbcbbf-… -> tree
refs/codex/turn-diffs/checkpoints/333d584d…/da3e2044-… -> tree

$ git ls-remote origin | wc -l          # 29 refs on the remote
29
$ git ls-remote origin | grep -c codex  # none of them are codex refs
0
```

Nine `refs/codex/turn-diffs/checkpoints/*` refs exist in this local clone, written by a local tool.
They point **directly at trees, not commits**, and they snapshot the untracked working directory —
including `tmp/`, which `.gitignore` correctly excludes from ever being committed.

That explains the contradiction between the two commands exactly:

| Command | Result | Why |
|---|---|---|
| `git log --all --pretty=format: --name-only \| grep -c '^tmp/'` | `0` | `git log` walks **commits**. A ref pointing at a tree contributes none. Correct answer for repository history. |
| `git rev-list --objects --all \| …` | finds the blobs | `--all` means every ref under `refs/`, and `rev-list --objects` traverses **objects**, so tree-refs are included. Correct answer for "what is in this local object store". |

Both are correct; they answer different questions. The audit asked the second and reported the
answer as if it were the first. The 82 MB `.git` measured locally is inflated by these local-only
refs; a clean clone is 25 MB.

**A second, independent methodological error** in the same section: `git rev-list --objects`
emits each object **once**, keyed by SHA, with only the first path at which it was found. Counting
its output therefore counts distinct *blobs*, not distinct *paths*. The audit labelled those counts
as paths, which produced "474 distinct paths" and the claim "there are not 99 PDFs in history."
Corrected inventory, path-based:

```
$ git log --all --pretty=format: --name-only | grep '^backend/storage/' | sort -u | sed 's/.*\.//' | sort | uniq -c | sort -rn
    300 json
     99 pdf
     11 png
      7 gitkeep
$ git log --all --pretty=format: --name-only | grep '^backend/storage/' | sort -u | wc -l
417
$ git rev-list --objects --all | grep -i '\.pdf$' | awk '{print $1}' | sort -u | wc -l
1
```

There **are** 99 PDF paths in history. They deduplicate to **one distinct blob** — one test document
committed 99 times. The underlying observation (a single PDF blob) was right; the framing drawn from
it was wrong.

**Method rule adopted for the rest of the engagement** (master spec §0 rule 9, with one addition):
history claims must carry their command and raw output — *and* must be scoped to what the remote
actually has. `--all` is not a safe proxy for repository history in a working clone. Verify with
`git ls-remote origin`, `git log --remotes=origin`, or a fresh clone before asserting anything is
"in history." Rule 9 as written would not have caught this error, because the command and output
were present and genuine; the scope was the defect.

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
| D3 student data in history | **NOT A DEFECT** | Superseded: the data is synthetic. The 99 PDF paths resolve to one **76-byte stub**; all 100 report records carry test-fixture names and `obtained_marks: 0.0`. See `docs/phases/PHASE_0_REPORT.md` §11. N1 below is retained for the record. |
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

### N1 — D3: the exposure is the JSON, not the PDFs; and the rewrite is PII-justified only

*(This section replaces a retracted earlier version — see §0.)*

Corrected inventory of `backend/storage/` across all history, path-based:

| Extension | Distinct paths |
|---|---|
| `.json` | 300 |
| `.pdf` | 99 paths / **1 distinct blob** |
| `.png` | 11 |
| `.gitkeep` | 7 |
| **Total** | **417** |

The 99 PDF paths are one test document committed 99 times, not 99 student scripts. Real, but a
single document.

**The 300 JSON files are the actual exposure.** `backend/storage/reports/*.json` carry identity
fields directly:

```json
{ "submission_id": "3c1e31a4-…", "student_name": "Status Test",
  "student_roll_number": "CS005", "exam_id": "003340e0-…", … }
```

and `backend/storage/ocr_outputs/*.json` carry extracted answer text with bounding boxes. Names +
roll numbers + answer content is precisely the DPDP-relevant set.

**Purge remains in scope, justified by PII alone.** Two consequences:

- **Gate 0(e) already passes.** A clean clone's `.git` is 25 MB against a 50 MB target, with no
  purge performed. Repository size is **not** a justification for the rewrite and must not be cited
  as one.
- **Scope is `backend/storage/**` only.** Not `tmp/**` — see §0.

Rewrite stays last, behind its approval gate, with `docs/HISTORY_REWRITE.md` written first.

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
| 0.5 | `.gitignore`: root `/storage/`, `/e2e_results.json`, `/tmp/`, `.next-prod/`, `*.pack`, `*.pack.old` | N2 |
| 0.6 | Implement the `AUTH_ENABLED`/`DEBUG`/`ENVIRONMENT=local` triple-gate; add `ENVIRONMENT` setting | N8 |
| 0.7 | Delete `backend/scratch_fix_db.py`, `backend/e2e_qa_test.py` | N3 |
| 0.8 | `docs/CREDENTIAL_ROTATION.md` (human checklist, no rotation performed by me) | Phase 0.4 |
| 0.9 | `docs/HISTORY_REWRITE.md` — scope `backend/storage/**`, PII-justified only (not size) — then ask before force-push | Phase 0.3, N1 |
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
- **Full PII content of the 300 storage JSONs.** Two were sampled (one `reports/`, one
  `ocr_outputs/`). The rest are inferred from path and naming convention, not read.
