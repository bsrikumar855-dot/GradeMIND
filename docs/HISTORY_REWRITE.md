# Git History Rewrite — Plan and Coordination

**Status: NOT EXECUTED. Awaiting approval.**
**Phase:** 0 (Containment), item 1.9
**Approver required:** Shreekumar
**Affected collaborators:** Vishi, Prabhu, Suchit, Santheesh, Tharun

This document exists so that nobody, including the person running the command,
discovers the consequences afterwards. A force-push to a shared repository
without warning is its own incident.

---

## 1. Why

**PII, and only PII.** Repository size is *not* a justification and must not be
cited as one — a clean clone is 25 MB against a 50 MB target, so Gate 0(e)
already passes with no rewrite performed.

The exposure is student data in `backend/storage/`, reachable from history even
though the working tree is clean (only `.gitkeep` files remain):

| Extension | Distinct paths in history |
|---|---|
| `.json` | 300 |
| `.pdf` | 99 paths / **1 distinct blob** |
| `.png` | 11 |
| `.gitkeep` | 7 |
| **Total** | **417** |

Reproduce:

```bash
# Question answered: which PATHS appear anywhere in commit history?
git log --all --pretty=format: --name-only | grep '^backend/storage/' | sort -u \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn

# Question answered: how many distinct BLOBS do the PDF paths resolve to?
git rev-list --objects --all | grep -i '\.pdf$' | awk '{print $1}' | sort -u | wc -l   # → 1
```

The 99 PDF paths are one test document committed 99 times. **The 300 JSONs are
the real exposure**: `backend/storage/reports/*.json` carry `student_name`,
`student_roll_number`, and `exam_id`; `backend/storage/ocr_outputs/*.json`
carry extracted answer text with bounding boxes. Names plus roll numbers plus
answer content is squarely within DPDP Act 2023 scope.

## 2. Scope

`backend/storage/**` — nothing else.

Explicitly **not** in scope:

- `tmp/**` — never committed to this repository. See §6.
- `frontend/.next-prod/**` and `frontend_backup/**` — already removed from the
  working tree, and not a PII concern. They can ride along in the same rewrite
  if desired, but they do not justify one on their own.

## 3. The command

Run on a **fresh mirror clone**, never on a working checkout:

```bash
git clone --mirror https://github.com/bsrikumar855-dot/GradeMIND.git GradeMIND-rewrite
cd GradeMIND-rewrite

# Verify the tool is the real git-filter-repo, not the deprecated filter-branch
git filter-repo --version

git filter-repo --invert-paths --path backend/storage/

# Confirm the paths are gone. Expect 0.
git log --all --pretty=format: --name-only | grep -c '^backend/storage/'
```

Then, and only after §4 is complete:

```bash
git push --force --mirror origin
```

## 4. Coordination — do these in order

1. **Announce.** Post to the team channel with a scheduled cutover time at
   least 24 hours out. Name this document.
2. **Everyone pushes or stashes.** Every collaborator pushes all work to a
   remote branch, or accepts losing it. Unpushed local commits do not survive.
3. **Freeze.** No pushes between the announcement and the all-clear. Merge any
   open PRs first, or accept that they must be recreated — PR refs do not
   survive a history rewrite, and GitHub may keep the old objects reachable via
   pull-request refs regardless.
4. **Back up.** Keep the pre-rewrite mirror clone offline until the team has
   confirmed the new history is good. This is the only rollback.
5. **Execute** §3.
6. **All-clear.** Every collaborator re-clones. Do **not** try to rebase an old
   clone onto the new history:

   ```bash
   # Correct
   cd .. && rm -rf GradeMIND && git clone https://github.com/bsrikumar855-dot/GradeMIND.git
   ```

7. **Post-rewrite.** Ask GitHub Support to garbage-collect the old objects.
   Until they do, the old commits remain reachable by SHA on github.com, which
   means **the PII is not actually gone from the hosting provider at the moment
   the force-push completes.**

## 5. What breaks if this is wrong

- Every collaborator's clone diverges irrecoverably; unpushed work is lost.
- Open PRs and any commit SHA referenced in an issue, CI run, or deployment
  record become dangling.
- Deployment tooling pinned to a SHA will fail until repointed.
- If the mirror backup is skipped and the filter is wrong, there is no undo.

## 6. Local object stores are NOT covered by this rewrite

A remote-side rewrite does not touch anyone's laptop. Two specific cases seen
on this project:

**Local-only tool refs.** This working clone carried nine
`refs/codex/turn-diffs/checkpoints/*` refs written by a local tool. They point
directly at **trees, not commits**, and snapshot the untracked working
directory. Consequences:

- `git log --all` does not see them (it walks commits; a tree-ref contributes
  none), so they are invisible to the usual history audit.
- `git rev-list --objects --all` **does** see them, because `--all` means every
  ref under `refs/` and `--objects` traverses objects.
- They held ~3.95 GB of untracked uvicorn logs, inflating `.git` to 82 MB
  locally while a clean clone was 25 MB.

Anyone who rewrites history and then assumes their local store is clean will be
wrong. To check and clear:

```bash
# Question answered: what is in this local object store, regardless of history?
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob"{print $3, $4}' | sort -rn | head -20

git for-each-ref --format='%(refname) -> %(objecttype)' | grep -v '^refs/heads\|^refs/remotes\|^refs/tags'
git for-each-ref refs/codex/ --format='%(refname)' | xargs -r -n1 git update-ref -d
git gc --prune=now
```

On this machine that took `.git` from 82 MB to 22 MB. Already done here; every
other dev machine needs it independently.

**Untracked artefacts on disk.** `tmp/` held 1.6 GB of unbounded dev-server
logs from ad-hoc shell redirection. `/tmp/` is now gitignored and the
pre-commit hook rejects any staged file over 5 MB, so these cannot reach
history — but they are still local PII risk, because they are request logs from
a student-data pipeline. See `docs/RUNBOOK_LOCAL_DEV.md` for the sanctioned way
to run the server.

## 7. Sign-off

| Step | Owner | Done |
|---|---|---|
| Announcement posted, cutover time set | Shreekumar | ☐ |
| All collaborators confirmed pushed | Vishi, Prabhu, Suchit, Santheesh, Tharun | ☐ |
| Open PRs merged or accepted as lost | Shreekumar | ☐ |
| Mirror backup taken and stored offline | | ☐ |
| Rewrite executed and verified | | ☐ |
| Force-push completed | | ☐ |
| All collaborators re-cloned | | ☐ |
| Local object stores cleaned (§6, per machine) | each dev | ☐ |
| GitHub Support asked to GC old objects | Shreekumar | ☐ |
