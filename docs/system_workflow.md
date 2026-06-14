# GradeMIND System Workflow

This document provides a holistic architectural view of GradeMIND, mapping component interactions, data flows, and end-to-end sequences.

---

## Component Interaction Diagram

This diagram displays the structural components of GradeMIND and their communication interfaces:

```mermaid
graph LR
    User[Client App: React/Next.js] -->|HTTPS| API[FastAPI Web Server]
    API -->|Read/Write| DB[(PostgreSQL)]
    API -->|Write Tasks| Broker[(Redis Broker)]
    Broker -->|Read Tasks| Worker[Celery Worker Nodes]
    
    API -->|Upload/Download| Storage[[Cloud Storage: S3/GCS]]
    Worker -->|Fetch Scans| Storage
    Worker -->|Write Reports| Storage
    Worker -->|Read/Write Status| DB
    
    Worker -->|REST API| OCR[Google Cloud Vision OCR]
    Worker -->|REST API| LLM[LLM Evaluation Engine]
```

---

## End-to-End Sequence Diagram

The following sequence diagram details the full lifecycle of an exam from creation to final report download:

```mermaid
sequenceDiagram
    autonumber
    actor T as Teacher
    actor S as Student
    participant FE as Frontend (UI)
    participant BE as FastAPI Backend
    participant DB as PostgreSQL DB
    participant GCS as Cloud Storage
    participant Q as Redis Queue
    participant W as Celery Worker
    participant AI as AI & OCR Engines

    %% Exam Setup Phase
    rect rgb(240, 245, 255)
        note right of T: Exam Setup Phase
        T->>FE: Create Exam ("Math Midterm")
        FE->>BE: POST /exams
        BE->>DB: Insert Exam Row
        DB-->>BE: Exam ID (10)
        BE-->>FE: HTTP 201 (Exam Created)
        T->>FE: Upload Question Paper & Key
        FE->>BE: POST /upload/question-paper & /upload/answer-key
        BE->>GCS: Write PDFs to Buckets
        BE->>DB: Update Exam status to READY
        BE-->>FE: HTTP 201 (Assets Uploaded)
    end

    %% Student Submission Phase
    rect rgb(245, 255, 245)
        note right of S: Student Submission Phase
        S->>FE: Upload Handwritten Answer Sheet
        FE->>BE: POST /upload/answer-sheet
        BE->>GCS: Save raw answer_sheet.pdf
        BE->>DB: Insert Submission (State = QUEUED)
        DB-->>BE: Submission ID (101)
        BE->>Q: Enqueue Task [evaluate_submission(101)]
        BE-->>FE: HTTP 202 (Accepted, Processing)
    end

    %% Background Processing Pipeline
    rect rgb(255, 245, 240)
        note right of W: Async Evaluation Pipeline
        W->>Q: Pull Task [evaluate_submission(101)]
        W->>DB: Update State to OCR_PROCESSING
        W->>GCS: Download student answer_sheet.pdf
        W->>AI: Send document to Google Vision API
        AI-->>W: Return OCR text coordinates & words
        W->>DB: Update State to EVALUATING
        W->>AI: Send Rubric, Keys, and OCR Text to LLM
        AI-->>W: Return Grading Scores & Feedback JSON
        
        alt Confidence Score >= 0.70
            W->>DB: Update State to COMPLETED & Save Scores
        else Confidence Score < 0.70
            W->>DB: Update State to PENDING_REVIEW & Save Scores
        end

        W->>AI: Send results to PDF Renderer (WeasyPrint)
        AI-->>W: Return compiled PDF binary
        W->>GCS: Save report.pdf to 'reports' bucket
        W->>DB: Save report_url to database
    end

    %% Report Delivery
    rect rgb(255, 255, 240)
        note right of S: Report Retrieval
        S->>FE: Click "View Report"
        FE->>BE: GET /submissions/{submission_id}/pdf
        BE->>DB: Verify Ownership / Permission
        BE->>GCS: Generate Signed URL
        GCS-->>BE: Returns secure CDN URL
        BE-->>FE: Redirects to secure CDN URL
        FE-->>S: Open Report PDF
    end
```

---

## Data Flow Diagram (DFD)

This diagram shows how data transforms as it moves through the system layers:

```mermaid
graph TD
    RawScan[Raw Answer Sheet File] -->|Upload| BackendAPI[API Upload Endpoint]
    BackendAPI -->|Write File| Storage[Cloud Bucket Storage]
    BackendAPI -->|Write Metadata| DB[(PostgreSQL Database)]
    
    Storage -->|Fetch Raw Bytes| OCRJob[OCR Preprocessing & Extraction]
    OCRJob -->|Raw Text JSON| SegmentJob[Segmentation Engine]
    SegmentJob -->|Segmented Answers JSON| EvalJob[AI Evaluation Module]
    
    EvalJob -->|Scoring Data & Feedback JSON| DB
    EvalJob -->|Scoring Data & Feedback JSON| PDFJob[PDF Report compiler]
    
    PDFJob -->|Binary PDF| Storage
    Storage -->|Signed PDF Link| Frontend[Client UI]
```
