# GradeMIND

AI-assisted grading for handwritten exam answer sheets. Upload a scanned
answer sheet, GradeMIND OCRs it, evaluates it against an answer key (or
autonomously, with no answer key at all), and produces a per-question score
breakdown with concept coverage, feedback, and a downloadable report.

- **backend/** — FastAPI + SQLAlchemy + PostgreSQL. JWT auth with refresh
  rotation, role guards (Teacher/Admin/Student), audit log.
- **AI/** — The evaluation engine: OCR (Tesseract baseline; optional
  EasyOCR/PaddleOCR/TrOCR for higher handwriting accuracy), an autonomous
  evaluator that grades from concept coverage with **no answer key and no
  API key required**, plus an optional Gemini cross-check layer.
- **frontend/** — Next.js 14 + React 18 + Tailwind + Recharts.

---

## Quick start (Docker Compose)

This brings up Postgres, the backend API, and the frontend together.

```bash
cp .env.example .env
```

Edit `.env` and set at minimum `POSTGRES_PASSWORD` and `SECRET_KEY` — the
containers will refuse to start without them (no insecure defaults). See
`.env.example` for what every variable does.

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

On first run, register a teacher account at http://localhost:3000/login
(there's a "Don't have an account? Register" toggle), then sign in.

The backend container runs `alembic upgrade head` before starting — Alembic
migrations are the schema source of truth for this (Postgres) deployment.

**What actually works end-to-end:** create an exam, upload its question
paper, upload a student's answer sheet (image or PDF), watch it process
(OCR → evaluate → report, polled live in the browser), then view the
per-question score/concept-coverage/feedback breakdown and download the
PDF report — all against the real API, no mock data.

**Note:** OCR accuracy with only the Tesseract baseline (what the Docker
image installs) is modest on messy handwriting. For the full multi-engine
router with real handwriting accuracy, see
[`backend/README.md`](backend/README.md#2b-ocr-engines--install-profiles)
for the optional heavy install profile — it isn't part of the default
Docker image because it pulls in PyTorch and multi-GB model downloads.

---

## Manual development setup

Run backend and frontend separately when iterating on code (faster reload
than rebuilding containers).

### Backend

See [`backend/README.md`](backend/README.md) for full setup (virtualenv,
PostgreSQL, Alembic, OCR install profiles). Quick version:

```bash
cd backend
python -m venv venv && venv\Scripts\activate   # or: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit DATABASE_URL, SECRET_KEY, etc.
alembic upgrade head
uvicorn app.main:app --reload
```

For a zero-Postgres local loop (e.g. running the test suite), SQLite works
without any setup — see "Tests" below.

### Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000 — you'll be redirected to `/login`.

---

## Demo mode (no login)

Setting `AUTH_ENABLED=False` on the backend makes every request act as an
anonymous admin — no login required anywhere. This is **only** for local,
throwaway demos. It is not the default, and must never be set in a shared or
real deployment: it disables every role guard and result-publishing access
check in the app.

---

## Tests

```bash
cd backend
DATABASE_URL="sqlite:///./test.db" SECRET_KEY="test" AUTH_ENABLED="True" \
  python -m pytest tests/ -q
```

```bash
python -m pytest AI/tests/ -q   # from the repo root
```

Both suites also run in CI on every push/PR — see
[`.github/workflows/tests.yml`](.github/workflows/tests.yml).

---

## Repository layout

```
backend/   FastAPI app: api → services → repositories → models
AI/        OCR + evaluation engine (importable standalone, no backend needed)
frontend/  Next.js app
docs/      Architecture and audit notes (verify against code — some predate
           recent changes)
```
