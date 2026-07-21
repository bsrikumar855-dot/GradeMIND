# GradeMIND Backend - Phase 1 Foundation

FastAPI production-ready backend foundation for GradeMIND, the AI-powered answer sheet evaluation platform.

## 1. Project Overview
This project sets up the foundational architecture for the GradeMIND Backend using FastAPI, Python 3.11, PostgreSQL, SQLAlchemy 2.0, Alembic, and Pydantic v2. It includes environment variable configuration, database session handling, health check endpoints, and database migration configurations.

---

## 2. Setup Instructions

### Virtual Environment Setup
From the `backend` directory, run:
```bash
python -m venv venv
```

To activate the virtual environment:
- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (CMD):**
  ```cmd
  .\venv\Scripts\activate.bat
  ```
- **Linux/macOS:**
  ```bash
  source venv/bin/activate
  ```

### Dependency Installation
Install the project requirements:
```bash
pip install -r requirements.txt
```

---

## 2b. OCR Engines & Install Profiles

Handwritten answer-sheet OCR is layered so the core app never requires heavy
ML dependencies:

- **Base install** (`requirements.txt`): gives you **Tesseract** OCR via
  `pytesseract`. This is enough to run the whole grading pipeline. Tesseract
  also needs the actual `tesseract-ocr` binary installed on the system
  (it's not a pip package):
  - Windows: [UB-Mannheim Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract`
  - Debian/Ubuntu: `apt-get install tesseract-ocr`
  - Docker: install `tesseract-ocr` in the image alongside the Python deps.

- **Full OCR profile** (`requirements-ocr.txt`): adds **EasyOCR**,
  **PaddleOCR**, and **TrOCR** (a handwriting-tuned transformer model) for
  significantly better handwriting accuracy via the 4-engine content-aware
  router (`AI/ocr/ocr_router.py`). These pull in **PyTorch**, are much
  larger installs, and TrOCR downloads ~1.3GB of model weights from
  HuggingFace on first use. Install with:
  ```bash
  pip install -r requirements.txt -r requirements-ocr.txt
  ```

If an engine's package or model isn't installed, its wrapper raises a clear
error and the OCR manager/router falls back to whichever engines *are*
available — grading still works with Tesseract alone, just at lower
handwriting accuracy.

**Sanity-checking OCR on an image** before trusting it for grading:
```bash
python -m AI.ocr.cli path/to/answer_sheet.jpg
```
This prints the extracted text with per-line confidence (and any detected
question segments). Run from the repository root so `AI` is importable, or
`PYTHONPATH=<repo-root>` from elsewhere. Use `--engine tesseract` to force a
single engine.

---

## 3. PostgreSQL Setup

1. **Install PostgreSQL** on your system (if not already installed).
2. **Create a database** named `grademind` (or configure your preferred name):
   ```sql
   CREATE DATABASE grademind;
   ```
3. **Configure the Database URL** in your `.env` file (see below).

---

## 4. Environment Variables
Copy `.env.example` to `.env` and configure the values:
```bash
cp .env.example .env
```

Ensure `.env` contains:
```env
DATABASE_URL=postgresql://<username>:<password>@<host>:<port>/grademind
SECRET_KEY=<your_secret_key>
DEBUG=True
PROJECT_NAME="GradeMIND Backend"
PROJECT_VERSION="1.0.0"
```

---

## 5. Running the Server
Start the development server using Uvicorn:
```bash
uvicorn app.main:app --reload
```
The server will start at `http://127.0.0.1:8000`.

---

## 6. API Documentation
Interactive API docs are available at:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 7. Alembic Migration Commands

1. **Generate the initial migration:**
   ```bash
   alembic revision --autogenerate -m "initial"
   ```
2. **Apply migrations to the database:**
   ```bash
   alembic upgrade head
   ```

---

## 8. Folder Tree
```
backend/
│
├── alembic/
│   ├── versions/
│   │   └── .gitkeep
│   ├── env.py
│   └── script.py.mako
│
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── database.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── session.py
│   │
│   ├── models/
│   │   └── __init__.py
│   │
│   ├── schemas/
│   │   └── __init__.py
│   │
│   ├── services/
│   │   └── __init__.py
│   │
│   ├── utils/
│   │   └── __init__.py
│   │
│   └── main.py
│
├── alembic.ini
│
├── requirements.txt
│
├── .env
│
├── .env.example
│
├── .gitignore
│
└── README.md
```

---

## 9. Verification Checklist
- [ ] Requirements.txt installs without conflicts.
- [ ] App starts successfully via `uvicorn app.main:app --reload`.
- [ ] `.env` configurations are loaded correctly and validated by Pydantic.
- [ ] Health Check endpoint returns 200 OK at `GET /` with the expected JSON payload.
- [ ] SQLAlchemy connects to the PostgreSQL database on startup.
- [ ] Alembic environment is active and successfully resolves database URL from `.env`.
