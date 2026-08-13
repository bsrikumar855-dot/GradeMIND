# Runbook — Running GradeMIND Locally

This exists because the ad-hoc pattern it replaces caused a real problem: a
dev server started with shell redirection wrote **1.6 GB** of unbounded logs to
a repo-relative `tmp/` directory, and those logs were request lines from a
pipeline that processes student answer sheets.

Nothing in the application can fully prevent that — `uvicorn ... > tmp/x.log`
is outside its control. Two guards exist, and both are backstops rather than
fixes:

- `/tmp/` is gitignored, so the artefact cannot be committed.
- The pre-commit hook rejects any staged file over 5 MB.

The actual fix is having a sanctioned way to run the server. This is it.

---

## Setup

```bash
python -m venv backend/venv
backend/venv/Scripts/activate        # Windows
# source backend/venv/bin/activate   # macOS / Linux

pip install -r requirements/base.txt -r requirements/ai.txt -r requirements/dev.txt
```

Optional handwriting engines (multi-gigabyte, pulls PyTorch):

```bash
pip install -r requirements/htr.txt
```

## Environment

Copy `.env.example` to `backend/.env` and fill it in. Never commit it — the
pre-commit hook rejects any `.env*` that is not `.env.example`.

`SECRET_KEY` and `DATABASE_URL` are required and have no defaults; the app
fails at import without them, which is intentional.

## Running the server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Do not redirect output to a file inside the repository.** If you need the log
persisted, send it somewhere out of the tree with rotation:

```bash
# Linux / macOS
mkdir -p ~/.grademind/logs
uvicorn app.main:app --reload --port 8000 2>&1 | rotatelogs ~/.grademind/logs/backend.%Y%m%d.log 86400
```

```powershell
# Windows PowerShell — out of tree, and check the size occasionally
$log = "$env:LOCALAPPDATA\GradeMIND\logs\backend.log"
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
uvicorn app.main:app --reload --port 8000 *>&1 | Tee-Object -FilePath $log
```

### Logs contain student data

Application logs are passed through `PIIRedactionFilter`
(`backend/app/core/log_redaction.py`), which redacts roll numbers, student
names, storage filenames, bearer tokens, and tokens in query strings. It is
covered by `backend/tests/test_log_redaction.py`.

That filter is a backstop, not permission. **Do not pass student identity into
a log call.** And note that anything you capture by shell redirection *before*
the app formats it — or from a tool that is not the app — is not filtered at
all.

## Tests

```bash
PYTHONPATH=. backend/venv/Scripts/python.exe -m pytest backend/tests -q
PYTHONPATH=. backend/venv/Scripts/python.exe -m pytest AI/tests -q
```

Lint and type gates, the same ones CI runs:

```bash
ruff check backend/app AI scripts
mypy AI/evaluation/embeddings.py
python scripts/check_compose_duplicate_keys.py docker-compose.yml
python scripts/check_no_self_skipping_tests.py
```

## Cleaning up a machine that has already accumulated logs

```bash
rm -rf tmp/
git for-each-ref refs/codex/ --format='%(refname)' | xargs -r -n1 git update-ref -d
git gc --prune=now
du -sh .git    # expect ~22-25 MB
```

The middle step matters and is easy to miss — see `docs/HISTORY_REWRITE.md` §6
for why local tool refs hold onto untracked files that `git log` cannot see.

## Docker

```bash
docker compose up --build
```

`docker-compose.yml` takes every secret from the environment with
`${VAR:?message}` and has no literals. A missing `SECRET_KEY` is a hard startup
failure by design.
