# GradeMIND — System State

**Written:** 2026-08-28 · **Commit:** `8cbf3fc` · **Branch:** `main`

The document a new contributor reads first. It records what is true, what is merely built, and what the docs still claim but is no longer so.

Verification tiers per `CLAUDE.md` §0: `LOCALLY-VERIFIED` (run here, output pasted) · `CI-VERIFIED` (run in CI, with URL) · `NOT RUN`.

---

## 1. What works — with the command that reproduces it

Admission test: can a command be run *right now* that demonstrates it? If not, it belongs in §2.

| # | Claim | Evidence | Reproduce |
|---|---|---|---|
| W1 | Scoring arithmetic is deterministic | 200 runs byte-identical, `sha256=cd3991d7cfc5485f` | `python -m scripts.verify_demo --offline` |
| W2 | Fixture matches its cache provenance | 2 pages verified against 5 cache entries | same |
| W3 | Pipeline reproduces documented regions/scores | Q13 3.0/3, 14/16 scoreable | same |
| W4 | Safety boundaries hold when triggered | 5/5 boundaries held | same |
| W5 | No adversarial regression | 36 probes, 12 failing, **0 new** | same |
| W6 | Annotated PDF produced and geometrically sane | 5/5 artifact checks | same |
| W7 | Suppression ratchet holds | `no new suppressed tests (6 skip, 6 xfail baselined)` | `python scripts/check_no_self_skipping_tests.py` |
| W8 | `ENVIRONMENT` triple-gate exists, defaults closed | `config.py:48` — `ENVIRONMENT: Environment = Environment.PRODUCTION`; validator `:88` | read `backend/app/core/config.py` |

`LOCALLY-VERIFIED` — full gate output, this machine, 2026-08-28:

```
  phase                        result   evidence
  1 ENVIRONMENT                PASS     all required packages present
  2 DETERMINISM                PASS     200 runs byte-identical, sha256=cd3991d7cfc5485f
  3 FIXTURE PROVENANCE         PASS     2 pages verified against 5 cache entries
  4 PIPELINE                   PASS     Q13 3.0/3, 14/16 scoreable
  5 SAFETY BOUNDARIES          PASS     5/5 boundaries held
  6 ADVERSARIAL                PASS     12/36 failing, 0 new
  7 ARTIFACTS                  PASS     5/5 artifact checks
  7/7 phases passed
```

**What the gate explicitly does not prove**, in its own words: accuracy, generalisation, transcription correctness, visual layout.

---

## 2. Built but unverified

| # | Component | Why it is not in §1 |
|---|---|---|
| U1 | Local HTR providers (TrOCR, Surya), line segmenter, benchmark pipeline | On `feat/local-htr-providers` — **pushed to origin 2026-08-28** at `0791827`. 1,248 lines. Still never run in CI and never merged. |
| U2 | HTR candidate survey + benchmark report | Same branch, now backed up. Amendment A's *first* deliverable. |
| U3 | Accuracy harness (bootstrap CIs, adversarial metrics) | Merged into `main`; validated against **no** ground truth. The numbers it emits are themselves untested. |
| U4 | Round-2 job state / resume / human-review persistence | In `main`, but job state lives in gitignored `tmp/jobs/` with CWD-dependent lookup. Not exercised by CI. |
| U5 | Student diagnostic report generator | In `main`. No test asserts report correctness end to end. |
| U6 | Container build + full import sweep (CI gate 0(b)) | Defined in `tests.yml`; **no run URL** obtainable from this machine. |
| U7 | Frontend workspace v2 (102 files, 7,173 insertions) | `wip/inflight-2026-08-20` — **pushed to origin 2026-08-28** at `9a074d7`. Never merged. Carries L16. |

---

## 3. Claimed in docs, no longer true

Live contradictions in `CLAUDE.md`. Correct them there.

| Doc claim | Reality | Evidence |
|---|---|---|
| "**`ENVIRONMENT` triple-gate — never built. No `ENVIRONMENT` setting exists.** (Track A1)" | **Built.** Setting, enum, default-to-PRODUCTION, and the three-way conflict validator are all present. | `backend/app/core/config.py:46,48,88,121,128` |
| "CI has no `--cov-fail-under`" (session premise) | **Present** at `--cov-fail-under=60` — but scoped to 3 backend service modules. `AI/` has **no coverage gate at all**. | `.github/workflows/tests.yml:99` |
| Limitation 19 — model-pin comment contradicts code | **Fixed on `main`.** Comment and constant agree, incident documented in place. | `AI/ocr/providers/gemini_vision.py:82-85` |
| Working base is `origin/post-round2-dev` | `post-round2-dev` is **82 commits behind `main`** and five weeks stale. `main` is the live line. | `git rev-list --left-right --count` |
| D3 "student data in history" | Already retracted; data synthetic. **A4 history rewrite not required.** | `PHASE_0_REPORT.md` §11 |

---

## 4. Limitations — deduplicated and renumbered

20 declared in `docs/DEMO_SCRIPT.md`, deduplicated to **16 live** plus 4 retired.

### A. No ground truth — the binding constraint

- **L1** — One student script, one exam, no human-marked ground truth. No accuracy claim is possible and none is made. *(was 1)*
- **L2** — Semantic thresholds are uncalibrated documented defaults, never derived from a labelled set. *(was 7)*

### B. Marking-scheme fidelity

- **L3** — 9 of 15 questions on the demo script have no marking scheme; not scored, not counted. *(was 2)*
- **L4** — **Q14/Q15 value points do not match the question paper.** The paper asks candidates to interpret attention mechanisms; the scheme credits CNN and LSTM. Those 3/3 results are not evidence of correctness. *(was 3)*
- **L5** — Paper says "answer any two" of Q13–15; the scheme models three as mandatory, under-crediting a student who followed the instruction. *(was 4)*
- **L6** — Neither scheme was authored blind. The DL scheme was AI-authored against the student's answer. *(was 5)*
- **L7** — The paper/scheme cross-check is lexical: it catches Q15 and **misses Q14**. The detector for L4 does not detect L4. *(was 20)*
- **L8** — Lift-detection finds 8 lifts in the DSA scheme and 3 in the DL scheme — backwards from what contamination predicts. It cannot separate canonical phrasing from copied phrasing. *(was 14)*

### C. Scoring engine defects

- **L9** — **12 of 36 adversarial probes fail**, in exactly 3 classes × 4 questions: `KEYWORD_SALAD` (4), `NEGATED` (4), `QUESTION_COPIED` (4). Each scores **full marks where 0 is allowed**. Containment detects presence, not assertion. *(was 6)*

### D. Transcription / OCR

- **L10** — Transcription is non-deterministic: same page, same pinned model, same prompt, different output across two runs. Measured twice. *(was 8)*
- **L11** — The segmenter read the examiner's own margin mark as a question number. Real ink, systematic. *(was 9)*
- **L12** — `rejoin_line_texts` joins lines with no space (`"solvea smaller"`, `"functionto map"`). Wrong 2 of 3 times on that page. Deterministic, and ours. *(was 10)*
- **L13** — The DSA answer sheet is a rendered font, not handwriting. `page_confidence` returned 1.0 on all 57 lines — what a self-reported legibility score does on synthetic input. No HTR claim derives from it. *(was 11)*

### E. Data plumbing

- **L14** — Identity masking removes page headers, destroying the page-1 section markers. Any segmentation depending on them must account for the band. *(was 12)*
- **L15** — `p3_evaluation_report.json` is lossy: character spans but no line bboxes, so a PDF regenerated from it alone has no highlights. *(was 13)*
- **L16** — `docker-compose.yml` carries 7 duplicate environment keys on `wip/inflight-2026-08-20`. YAML does not error; the last value silently wins. *(was 18)*

### Retired — fixed or quarantined, retained for provenance

> **These three were retired prematurely.** Until 2026-08-28 all of 15, 16 and 17 were still
> live on `main` inside the duplicate `backend/AI/` tree — see §7. They are retired now.

- ~~15~~ Groq evaluator took the mark straight from the model's JSON reply. Root `AI/` refuses at
  construction via `LLMMarkingDisabled`; the shadow copy had **zero** occurrences of that symbol.
  Full pipeline preserved on `archive/groq-baidu-pipeline`.
- ~~16~~ OCR engine tokenized the file **path**, not the image; hardcoded `confidence=0.92`. Still
  wired as **primary #1** in the shadow `ocr_router.py`.
- ~~17~~ Availability probe performed a network call to huggingface.co — reachable through the same
  shadow router.
- ~~19~~ Model pin silently reverted with the explaining comment left intact — **fixed** in
  `7735a53`. The shadow copy carried the correct value with the warning comment stripped.

---

## 5. Branch inventory and disposition

From `git for-each-ref` and `git rev-list --left-right --count main...<branch>`, 2026-08-28.

### Merged — 0 commits ahead of `main`

| Branch | Behind | On origin? | Disposition |
|---|---|---|---|
| `feat/r2-progress-preservation` | 6 | **no** | MERGED — content in `main` (`4ed45d6`). Safe to delete. |
| `feat/student-report` | 5 | **no** | MERGED — content in `main` (`d4d0f48`). Safe to delete. |
| `eval/accuracy-harness` | 57 | yes | MERGED — `test_eval_metrics.py` and `test_eval_adversarial.py` confirmed present in `main`'s tree, not merely in its history. |
| `feat/workspace-wiring` | 10 | **no** | MERGED. Safe to delete. |
| `demo/value-point-engine` | 59 | yes | MERGED. |
| `feat/analytics-page` | 81 | yes | MERGED. |
| `feat/frontend-v2` | 22 | yes | MERGED. |
| `feat/gemini-vision-htr` | 29 | yes | MERGED. |
| `fix/ocr-zero-line-guard` | 63 | yes | MERGED. |
| `hotfix/remove-run-cmd-rce` | 93 | yes | MERGED. |
| `sprint/demo-final` | 28 | yes | MERGED. |
| `verify/demo-harness` | 27 | yes | MERGED. |
| `feature/ai-core-v1` | 99 | yes | MERGED. |

**Merged but must not be deleted** — load-bearing by reference:

- `archive/groq-baidu-pipeline` (0 ahead, 21 behind) — **KEEP.** Reference for retired limitations 15–17. Confirmed safely on origin: local and origin both at `10efc589`. Leave alone.
- `prod/phase-0-containment` (0 ahead, 70 behind) — **KEEP.** `CLAUDE.md` names it as the branch point for Track B.
- `post-round2-dev` (0 ahead, 82 behind) — **KEEP** until `CLAUDE.md` is corrected to name `main`.
- `release/ai-platform-v1` (0 ahead, 82 behind) — **KEEP.** Named in docs; stale at `d799b0f`.

### Not merged — carries unique commits

| Branch | Ahead | On origin? | Disposition |
|---|---|---|---|
| `feat/local-htr-providers` | **2** | **yes** (pushed 2026-08-28, `0791827`) | **WORTH MERGING.** 1,248 lines of Phase 3 HTR: TrOCR and Surya providers, line segmenter, benchmark pipeline, candidate survey, benchmark report. No longer at risk of loss. |
| `wip/inflight-2026-08-20` | **1** | **yes** (pushed 2026-08-28, `9a074d7`) | **DECIDE.** 102 files, 7,173 insertions of frontend v2. Carries L16. |
| `fix/log-redaction-token-shapes` | 1 | yes | WORTH REVIEWING — redaction by construction; a superset may already be in `main`. |
| `feat/ai-evaluation-engine` | 1 | yes | DEAD — the single commit is `chore: remove generated storage artifacts`. |

### Origin-only branches never fetched locally

`Meenakshi` · `Naksh` · `Nakshatra` · `OCR` · `Vishwanath` · `vishwanath` · `devops-setup-10449465089859295896` · `feat/exam-management-module-…` · `feat/explainability-2.0`.

All pre-July and unassessed except as noted.

**The `Vishwanath` / `vishwanath` case collision is already active, not theoretical.** On this Windows machine both remote-tracking refs had already collapsed onto one SHA, so `origin/Vishwanath` and `origin/vishwanath` both resolved to `13093a9c` while `origin` genuinely held two different commits:

```
d0914fbe...  refs/heads/Vishwanath     (2026-06-14, "sdf")
13093a9c...  refs/heads/vishwanath     (2026-08-22, "Supabase for db")
```

The capital-V branch was not a duplicate — it carried **one commit reachable from neither `main` nor the lowercase branch**: a `Front end/` scaffold with a directory name containing a space. Reaching it required fetching `refs/heads/Vishwanath` explicitly to a non-colliding local ref, because the tracking ref was unusable.

`d0914fb` is now preserved at **`archive/vishwanath-frontend-june-2026`** on origin.

**Decision: do not delete `refs/heads/Vishwanath`.** It is a teammate's branch, the archive already preserves its unique commit, and the collision only affects local checkouts on case-insensitive filesystems — nothing server-side is broken. The mitigation is a note in `README.md` telling anyone cloning on Windows or macOS how to fetch the hidden ref explicitly. Deleting a collaborator's branch out from under them to solve a local-checkout annoyance is a poor trade; the branch is Vishi's to remove.

**No branches were deleted this session.** Rationale in the session report, Task 2.

---

## 6. What blocks each remaining phase

| Phase | Blocker |
|---|---|
| **Track A closeout** | Gate 0(e) probe (peak RSS **and** peak disk) unwritten. Lockfile blocked: Windows/3.14 dev vs Linux/3.12 CI. Four CI gates have no run behind them. The `ENVIRONMENT` gate is **done** — update the tracker. |
| **Track B** (transcription capture) | Was gated on A4. **A4 is closed as not required**, so B is unblocked now. Branch from `prod/phase-0-containment` to reuse `log_redaction.py`. |
| **Track C** (marking-scheme engine) | Was gated on A4 — **unblocked**. Track C is the fix for L9: value-point detection replaces containment scoring. Critical path C1→C2→C3→C5. |
| **Phase 1** (identity, audit, async) | After Track C. D5 (3 sites) and D13 (3 sites) remain open and are Phase 1 scope. |
| **Phase 3** (HTR) | GPU booking on `techpark-9` from Shreekumar — a scheduling blocker, not a technical one. First action regardless: push `feat/local-htr-providers`. |
| **Phase 4** (lanes, double marking) | Needs Track C's `MatchResult` / `QuestionScore` contract. |
| **Phase 5** (human interfaces) | Needs Phase 4 lanes. WCAG 2.1 AA throughout. |
| **Phase 6** (scale, QA, release) | **Blocked on the golden set.** The QWK gate stays dark until a labelled set exists. |

**The single binding constraint across Phases 3, 4 and 6 is the golden set.** Until it exists there is no accuracy figure, no calibrated threshold, and no defensible `AUTO` lane.

---

## 7. Resolved 2026-08-28 — the duplicate `backend/AI/` tree

Recorded because the mechanism generalises, not because the fix was hard.

`backend/AI/` was a 94-file copy of the repo-root `AI/` package: 90 blobs byte-identical, 4 diverged, and **every divergence in the direction of less safety**.

`AI/` has no `__init__.py`, so it is a **namespace package**. That is the part that made this dangerous. A namespace package does not let one directory shadow another — it **merges** them into a single `__path__`. Measured on `8cbf3fc`, with the process started in `backend/`:

```
path from backend/:  ['D:\GradeMIND\backend\AI', 'D:\GradeMIND\AI']
```

Both trees live inside one package, shadow first. So `AI.evaluation.groq_evaluator` came from the copy with no kill switch while `AI.evaluation.embeddings` came from the real one, and nothing at any import site showed which was which.

The kill switch is not decoration. Root `AI/evaluation/groq_evaluator.py:81` refuses at construction unless `GROQ_ALLOW_LLM_MARKING=true`, because the class lifts `score_awarded` straight out of an LLM reply — no criterion id, no evidence span, no arithmetic — and so cannot satisfy master spec rule 3. It also defaults a missing score to `0.0` and a missing confidence to `0.95`. The shadow copy had **zero** occurrences of `LLMMarkingDisabled`.

Demonstrated, not inferred. With the shadow restored, the parameterised guard test fails from `backend/` and passes from the repo root:

```
AssertionError: the AI package reachable from D:\GradeMIND\backend has no
LLMMarkingDisabled symbol. That is the signature of the stripped shadow copy:
the deleted backend/AI/ tree contained zero occurrences of it.
```

**Resolution.** `backend/AI/` deleted outright — it was a strict subset of `AI/` with no unique files and nothing anywhere referenced the path. The container already copies root `AI/` to `/app/AI` and sets `PYTHONPATH=/app`, so imports resolve with the shadow gone.

**Guard.** `backend/tests/test_single_ai_tree.py` — four tests, verified to fail when the tree is restored:

1. `backend/AI/` does not exist on disk.
2. `AI.__path__` contains exactly one directory, from both the repo root and `backend/`.
3. `AI.evaluation.groq_evaluator` resolves to the same file from both.
4. `GroqEvaluator()` raises `LLMMarkingDisabled` from both.

Subprocess tests on purpose: the failure mode is interpreter start-up state — cwd landing on `sys.path` ahead of `PYTHONPATH` — which an in-process import cannot reproduce.

**A second defect found while fixing the first.** CI's gate 0(b) import sweep passed `pkgutil.walk_packages(['AI','app'], '')` — *relative* paths, with `WORKDIR=/app/backend`. It was therefore sweeping `/app/backend/AI`, the shadow, and never the real tree. Worse, `walk_packages()` yields nothing for a non-existent path and raises nothing, so once the shadow was deleted the gate would have gone on printing `ALL IMPORTS OK` while importing zero `AI` modules. Now uses each package's own `__path__`, asserts `AI` resolves under `/app/AI`, and asserts a minimum module count — a sweep that sweeps nothing must fail rather than pass quietly. `NOT RUN`: needs Docker, unavailable on this machine.

**Gate after the change:** `LOCALLY-VERIFIED`, `python -m scripts.verify_demo --offline` → **7/7 phases passed**, exit 0.

### RETRACTED 2026-08-28 — "the shadow was breaking the safety tests"

An earlier revision of this section claimed that deleting `backend/AI/` fixed five tests in `test_htr_pipeline.py` — the DPDP masking boundary, raise-instead-of-silent-zero, the `AUTO` confidence floor, and provenance completeness — and read significance into which five they were. **That claim was wrong and is withdrawn.**

It came from comparing `AI/tests/` in a throwaway `main` worktree (20 failures) against the working tree (15). Those two environments differ in **two** variables, not one: the shadow tree, and the gitignored `tmp/` state that the HTR fixtures depend on and that a fresh worktree does not have. The delta was attributed to the variable under investigation.

Re-measured with exactly one variable changed — same directory, same cwd, `backend/AI` moved aside and moved back:

```
AI/tests, shadow PRESENT :  18 failed, 364 passed
AI/tests, shadow PARKED  :  18 failed, 364 passed
diff of failure sets     :  no difference
```

Run from the repo root, `AI.__path__` never includes `backend/AI`, so the shadow cannot affect `AI/tests` at all. The five `test_htr_pipeline.py` failures are caused by the missing `tmp/` state in a fresh checkout — a real finding, but a different one, and it belongs to the gitignored-demo-dependency problem rather than to this section.

This is the same failure mode as D3, committed by the same process that documented D3: a measurement inherited a scope it never declared. The corrective rule is unchanged and was simply not applied — state which question the command answers. `pytest` in a fresh worktree answers "what fails in a checkout without `tmp/`", not "what does the shadow break".

**The deletion itself remains correct** and rests on evidence that was never in doubt: the shadow's `groq_evaluator.py` contains zero occurrences of `LLMMarkingDisabled`, demonstrated by restoring the tree and watching the guard test fail from `backend/` while passing from the repo root. Nothing above weakens that.

### Where the shadow *does* bite: `verify_demo`

Found 2026-08-28 while working on `fix/6b-negation`, and this one is measured with a single variable.

`scripts/verify_demo.py:38` does `sys.path.insert(0, str(ROOT / "backend"))`. Because `AI/` is a namespace package, that **merges** `backend/AI` ahead of `AI/`:

```
AI.__path__    : ['D:\GradeMIND\backend\AI', 'D:\GradeMIND\AI', 'D:\GradeMIND\AI']
score_computer : D:\GradeMIND\backend\AI\evaluation\score_computer.py
has negation   : False
```

**The demo harness resolves the scorer to the shadow copy.** On `main`, `verify_demo`'s `7/7` is a statement about `backend/AI/`, not about the engine under development. A change to `AI/evaluation/score_computer.py` can be fully landed and the harness will report `7/7` without ever executing it — which is exactly what happened on the first run of the negation work, where the adversarial phase reported `NEGATED 0 pass / 4 fail` against a scorer that had the fix.

That is a gate reporting on code that is not the code under test. Deleting `backend/AI/` fixes it; until this branch lands, `verify_demo` results on `main` should be read as validating the shadow tree.

The general lesson matches the D3 entry in `CLAUDE.md`. Four consistent measurements — 94 paths, 90 identical blobs, "nothing imports `backend.AI`", and a green gate — all agreed the duplicate was inert. They agreed because none of them had opened the four files that differed. A count of paths is not a statement about what is in them.
