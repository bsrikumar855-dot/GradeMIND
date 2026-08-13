# GradeMIND — Engagement Context

Inherited by every session. Read before touching anything.

**What this is:** converting a hackathon MVP into a system that assigns marks to real students on
real board-exam scripts. A wrong mark here is not a bug, it is a wronged student with a legal right
to appeal. Behave accordingly.

**Repo:** `https://github.com/bsrikumar855-dot/GradeMIND.git`
**Working base:** `origin/post-round2-dev` (**not** `main`, and **not**
`origin/release/ai-platform-v1` — that name is stale at `d799b0f`)

---

## §0 — Operating rules

1. **Never claim a phase is done without running its verification gate and pasting the raw output.**
   Not a summary of the output. The output.
2. **Never fabricate a score, a confidence value, or a test result.** If a component cannot produce
   a defensible number, it must raise, not guess.
3. **Every mark awarded must be traceable** to (a) a marking-scheme criterion ID, (b) a character
   span in the extracted answer text, (c) the engine version that produced it. If you cannot
   produce that triple, do not award the mark.
4. **Deterministic core, LLM language layer.** The LLM may extract, paraphrase, classify, and
   explain. The LLM may **never** be the sole authority on a numeric mark. Marks come from
   deterministic rubric arithmetic over LLM-extracted evidence. This separation is the
   architectural spine — if a design choice violates it, reject the design choice.
5. **Work on a branch per phase.** `prod/phase-N-<slug>`. Open a PR per phase. **Do not push to
   `main`.** (Pushing feature branches is expected and correct.)
6. **Do not delete or rewrite files outside the phase's declared scope.** If you believe a file
   outside scope must change, stop and ask.
7. **If a phase's spec is ambiguous, stop and ask one specific question.** Do not resolve ambiguity
   by guessing and proceeding.
8. **Before starting any phase, `git log --oneline -5` and `git status`,** and confirm you are on
   the expected base. Do not trust your own memory of repo state across sessions.
9. **History-forensics claims carry their command, their raw output, and their scope.**

   Any claim about repository history, blob sizes, object counts, or file contents must be
   accompanied by the exact command that produced it and its unedited output.

   **And must be scoped to what the remote actually has.** `--all` means every ref under `refs/`,
   including local-only tool refs, stashes, and refs that point at trees rather than commits. It is
   not a proxy for repository history in a working clone. Verify with `git ls-remote origin`,
   `git log --remotes=origin`, or a fresh clone before asserting anything is "in history."

   **And must state which question the command answers.** `git rev-list --objects --all` answers
   "what is in this object store"; `git log --all --name-only` answers "what is in this
   repository's history." The distinction is invisible in the output — nothing about
   `08896a52… untracked_big.log` tells you it came from a tree-ref.

   *This rule exists because of a real incident: a genuine command with genuine output was reported
   as repository history when it was actually local `refs/codex/turn-diffs/checkpoints/*` tree-refs
   holding untracked files. Rule 9's first clause alone would not have caught it.*

### Verification tiers — always both, never blurred

| Tier | Meaning |
|---|---|
| `LOCALLY-VERIFIED` | Run on this machine, raw output pasted |
| `CI-VERIFIED` | Run in CI, **with the run URL** |
| `NOT RUN` | Neither. Say so, with the reason. |

Never write plain "passed." A gate honestly marked `NOT RUN` is worth more than one that blurs the
tiers — blurring is how a gate becomes decorative.

---

## Current state

**Phase 0 (Containment):** items 1.1–1.8 complete on `prod/phase-0-containment` @ `d429465`.
Item 1.9 (history rewrite) is documented in `docs/HISTORY_REWRITE.md` and **NOT executed** —
it requires explicit per-session approval.

Read these before starting anything:

- `docs/audit/BASELINE_AUDIT.md` — verified defect status, new findings, §0 retraction notice
- `docs/phases/PHASE_0_REPORT.md` — gate results by tier, and where delivered work is narrower
  than the gate as written
- `docs/HISTORY_REWRITE.md` · `docs/CREDENTIAL_ROTATION.md` · `docs/RUNBOOK_LOCAL_DEV.md`

### Defect status

| ID | Status |
|----|--------|
| D1 RCE | FIXED — `frontend/src/app/api/` no longer exists at all |
| D2 auth bypass | FIXED (default only) — see `ENVIRONMENT` gate below, still outstanding |
| D3 student data in history | **Tree clean, history not.** 300 JSONs with `student_name` + `student_roll_number`; 99 PDF paths → **1 distinct blob** (one test document). Purge is PII-justified only. |
| D4 requirements | FIXED — `requirements/{base,ai,htr,dev}.txt`, exact pins |
| D5 name-based authz | **PRESENT — 3 sites.** `student_service.py:66` (unescaped `ilike`), `:96` (returns `student_id = student_name`), `:124` (name equality). Phase 1.1. |
| D6 no CI | FIXED, hardened in Phase 0 |
| D7 verification thresholds | **PRESENT.** Absolute marks, unreachable `conf_diff` branch. Phase 4.3. |
| D8/D9 heuristics | **PRESENT.** In the scoring path. Phase 2.5 / Track C5. |
| D10 build cache | FIXED |
| D11 CORS regex | FIXED — explicit env allowlist, regex removed |
| D12 upload buffering | FIXED — `BodySizeLimitMiddleware` on the raw ASGI receive stream |

### Outstanding from Phase 0

- **`ENVIRONMENT` triple-gate** — never built. No `ENVIRONMENT` setting exists. (Track A1)
- **Gate 0(e) probe** — not written. Must assert **peak disk as well as peak RSS**. (Track A1)
- **Lockfile** — blocked on this machine (Windows/3.14 vs Linux/3.12 container). (Track A3)
- **Four CI gates** — 0(b), 0(c), 0(e), 0(f) have no run behind them. (Track A2)
- **Full backend suite** — not re-run since the final Phase 0 edits. The "120 passed / 1 failed"
  figure is **stale**; do not carry it forward.
- **Upstream body cap** — nginx `client_max_body_size` or platform equivalent. Not in this repo;
  needs an owner.

---

## Shipping posture: ASSIST-ONLY

**No golden set exists.** No `golden`, `ground_truth`, or `marking_scheme` fixtures on any branch.
Nothing labelled. This is a decided constraint, not a temporary gap, and it shapes every phase:

- **`AUTO` lane is disabled at config level.** Every question routes `REVIEW` or
  `MANDATORY_HUMAN`. The system suggests marks with full derivations; a human awards them.
- **Phase 3 makes no accuracy claim.** No CER figure. The gate is "provider interface exists, is
  swappable, propagates per-line confidence."
- **Phase 2 semantic thresholds ship as documented, UNCALIBRATED defaults** with a flag that
  propagates into `MatchResult` and forces the question out of `AUTO`.
- **Phase 6 QWK gate** is "the harness exists and runs in CI," dark until a labelled set arrives.

A system that honestly ships assist-only marking is a real product. A system that claims autonomous
CBSE-grade evaluation and quietly guesses on handwriting it cannot read is a liability with a UI on
top.

**The path off assist-only** is Track B: capture every examiner correction as a labelled pair.
Assist-only mode generates the dataset that unlocks `AUTO`. Cheap now, expensive to retrofit.

**If you conclude a target is not achievable with available data, models, or time — say so directly
and propose the reduced scope.**

---

## Target system

**Scale:** 500,000 scripts/cycle, 10–20 pages each. Peak ingest 5,000 scripts/hr; steady evaluation
≥2,000 scripts/hr; P95 end-to-end ≤4 min. **Evaluation is always asynchronous** — no HTTP request
ever waits on OCR or an LLM call.

**Defensibility:** every mark is appealable. The system must reconstruct, for any question of any
script: marking-scheme criterion → matched evidence span (page + bbox) → arithmetic → final mark.

**Lanes:** `AUTO` | `REVIEW` | `MANDATORY_HUMAN`, deterministic and auditable. Blind double
evaluation on a configurable sample (default 5%) plus 100% of `REVIEW`.

**Marking-scheme fidelity** is the single biggest gap between current code and target. CBSE
evaluation is not "does the answer resemble the key" — an official scheme allocates marks to
specific value points with explicit rules for alternatives, partial credit, and "any three of the
following." The evaluator's job is **value-point detection**, not similarity scoring.

**Compliance:** India DPDP Act 2023. **Evaluation runs on anonymized text** — identity stripped
before the evaluator sees the answer, re-attached only at result assembly. The existing
`IDENTITY_PATTERNS` pass is the seed; promote it to a hard architectural boundary with a test that
fails if identity fields reach the evaluator. Immutable append-only audit log for every mark change.

**Architecturally sound, must be preserved:** the `api → services → repositories → models/schemas`
layering; Alembic migration discipline; the fairness pre-pass (`IDENTITY_PATTERNS`,
`PROTECTED_TERMS`) that runs before evaluation; `VerificationEngine` as a pure observer that never
mutates `score_awarded`.

---

## Spec Amendment A — self-hosted, unmetered HTR

**Replaces §2.4 and Phase 3 of the original spec.**

Goal: no per-page metering, no third-party dependency on the critical path. Be precise about what
that buys:

- **Removes marginal cost per page. Does not remove cost.** 500,000 scripts × ~15 pages =
  **7.5M pages/cycle**. At 1 page/sec on one GPU that is 87 days of continuous compute. Throughput
  planning is first-class in this phase.
- **Transfers accuracy risk onto us.** Hosted document-intelligence APIs are materially better on
  unconstrained handwriting, particularly Indic and mixed Hindi/English scripts. Self-hosting is
  defensible; pretending it is accuracy-neutral is not.
- **Makes reproducibility easier.** Pinned local weights with a recorded hash satisfy Phase 2.6 in
  a way a versionless hosted endpoint never can. **Lead with this argument.**
- **Does not unlock `AUTO`.** Only a labelled golden set does.

### Hardware reality

Development target is a single **RTX 5070 (12 GB, Blackwell) on `techpark-9`**, with a resident
process already consuming significant VRAM.

- A 7B-class VLM in bf16 needs ~16 GB and **will not fit.** Plan for 4-bit quantisation (~6–7 GB)
  or a smaller model. Benchmark quantised vs full precision on real pages and report the CER delta.
- Blackwell needs a recent CUDA/PyTorch pairing. Pin exact CUDA, driver, and torch versions in
  `requirements/htr.txt` and the worker Dockerfile. Record them on every evaluation record.
- **Dev hardware is not capacity planning.** Produce a separate sizing model for 7.5M pages:
  measured pages/sec/GPU, GPUs required for a 14-day cycle, rental cost of that fleet. Publish the
  number even if uncomfortable.

> **Scheduling dependency:** `techpark-9` is not reachable from the dev machine and is shared with
> Vishi's and Suchit's jobs. The candidate survey and throughput benchmark need booked GPU time
> from Shreekumar — this is a scheduling blocker, not something to work around.

### Architecture

`HTRProvider.extract(page_image, hints) -> Page{lines: [Line{text, confidence, bbox, script}],
page_confidence, provider, model_version, weights_sha256}`

Four local implementations, no network calls at inference time: (1) printed/structured text — CTC
stack, solved, don't linger; (2) handwriting Latin — TrOCR-class; (3) handwriting Indic/mixed —
quantised VLM, **concentrate effort here**; (4) layout/reading order — separate model, run
*before* text extraction so you can debug which stage failed.

Selection is config-driven, per subject and page-class. No hardcoded provider in the evaluation
path.

**Do not pick models from memory — including mine.** The open-weight OCR/VLM landscape moves fast
and my knowledge has a cutoff. First deliverable is a **candidate survey**: benchmark ≥4 current
open-weight options on held-out real pages, report CER/WER per candidate with the exact commit or
weights hash tested, *then* choose. A model named in a spec is a starting point for a search, never
a decision.

### Serving

GPU workers are a separate service from the API and CPU workers, scaled independently. Batched
inference with a dynamic batcher, **per-page jobs not per-script** (a 20-page script must
parallelise). Model resident per worker process. Bounded queue with backpressure — a full GPU queue
returns `429` at ingest, it does not silently accumulate. Deterministic inference: fixed seed,
temperature 0, `torch.use_deterministic_algorithms(True)` where kernels allow. **Where determinism
is not achievable, say so explicitly in the phase report** as a known limitation against Phase 2.6.
Page-level cache keyed on `(page_sha256, model_version, preprocess_version)`.

### Preprocessing (CPU, cheap, highest ROI in the phase)

Deskew · denoise · ruling/margin removal · orientation detection · per-page quality score. The
quality score gates everything downstream: a page below the floor routes to `MANDATORY_HUMAN`
before a GPU cycle is spent. Most HTR failures are input-quality failures.

### Failure taxonomy — mandatory

`BLANK_PAGE` · `ILLEGIBLE` · `WRONG_ORIENTATION` · `MISSING_QUESTION_NUMBER` · `SCRIPT_MISMATCH` ·
`PAGE_COUNT_MISMATCH`. **None may silently produce a zero.** Every one routes to
`MANDATORY_HUMAN`.

### Gate 3 (revised — no accuracy claim)

Provider swap by config only · zero network egress at inference · confidence propagates end-to-end
and blocks `AUTO` below floor · every failure fixture routes correctly and none produces a zero ·
100-run byte-identical reproducibility · **measured** throughput published plus 7.5M-page fleet
sizing · candidate survey with per-model CER on a stated dataset, **or** an explicit "no labelled
data — no accuracy claim made."

---

## Phase / track map

Phase 1's async rewrite comes **after** Track C, not before — landing a queue on top of an
evaluation core about to be replaced is work partly redone.

| Track | Content | Depends on |
|---|---|---|
| **A** Phase 0 closeout | A1 `ENVIRONMENT` gate + 0(e) probe + full suite · A2 CI green + read back · A3 lockfile via CI · A4 history rewrite | A4 needs explicit approval |
| **B** Transcription capture | Amendment A §2.7 — data layer + API only, no UI | none; start immediately, parallel to A |
| **C** Marking-scheme engine | C1 schema/state machine · C2 `ScoreComputer` · C3 `ValuePointMatcher` · C4 ingestion · C5 integration | starts after A2; C1→C2→C3→C5 critical path, C4 any time after C1 |
| Phase 1 | Identity, audit, async | after Track C |
| Phase 3 | HTR (Amendment A) | GPU booking |
| Phase 4 | Orchestration, lanes, double marking | |
| Phase 5 | Human interfaces (WCAG 2.1 AA — examiners work 8-hour shifts) | |
| Phase 6 | Scale, QA, release | |

---

## Standing constraints

- Python 3.11+ (**CI runs 3.12**; the dev machine has 3.14 — mypy's `python_version` is pinned to
  3.12 in `pyproject.toml` to match CI, because numpy's bundled stubs use 3.12-only syntax).
- `ruff` and `mypy` gates are **scoped and ratcheting**, not absolute. Ruff defaults report 1065
  findings on this codebase and `mypy --strict AI/` cannot resolve the package. Enforced today:
  ruff `E9`/`F821`/`F811`/`F5xx`, mypy per-module. Backlog and rationale in `pyproject.toml`. The
  rule set may grow, never shrink.
- **No new hardcoded thresholds.** Every number affecting a mark lives in versioned config with a
  documented derivation.
- **No `except Exception: pass`. No silent fallbacks in the scoring path.** A fallback that changes
  marks is not a fallback, it is an unlogged scoring change. (See `AI/evaluation/embeddings.py` for
  the shape this should take: raise, record provenance, let the job retry or dead-letter.)
- Migrations reversible and tested against a production-shaped dataset.
- **Every PR states its blast radius:** what breaks if this is wrong.
- Self-skipping tests are ratcheted by `scripts/check_no_self_skipping_tests.py` against
  `scripts/self_skipping_tests_baseline.txt`. The baseline may shrink, never grow.

## Output format per phase

`docs/phases/PHASE_N_REPORT.md`: files changed · commands run · **raw gate output, by tier** ·
known gaps · what the next phase depends on.
