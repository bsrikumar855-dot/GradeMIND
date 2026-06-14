# GradeMIND API Contracts

This document outlines the API specifications for the GradeMIND Backend. All endpoints return standardized response payloads and use HTTP status codes for status reporting.

---

## Authentication APIs

### 1. Register User
- **Endpoint**: `POST /auth/register`
- **Purpose**: Registers a new user (Admin, Teacher, or Student) in the system.
- **Authentication**: None.
- **Request Body** (`application/json`):
  - `name` (string, required): Full name of the user.
  - `email` (string, required): Valid email address.
  - `password` (string, required): Password (min 6 characters).
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "User registered successfully"
  - `data` (object):
    - `id` (integer): Auto-generated user identifier.
    - `name` (string): Registered user's name.
    - `email` (string): Registered user's email.
    - `role` (string): User role (e.g. STUDENT, TEACHER, ADMIN).

#### Success Example (Status 201 Created)
```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "id": 1,
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "role": "TEACHER"
  }
}
```

#### Error Example (Status 422 Unprocessable Entity)
```json
{
  "success": false,
  "message": "Validation failed: [body -> email]: value is not a valid email address",
  "errors": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

---

### 2. Login User
- **Endpoint**: `POST /auth/login`
- **Purpose**: Authenticates credentials and returns a JWT token.
- **Authentication**: None.
- **Request Body** (`application/json`):
  - `email` (string, required): User email address.
  - `password` (string, required): Plaintext password.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Login successful"
  - `data` (object):
    - `access_token` (string): Valid JWT Bearer token.
    - `token_type` (string): "bearer"

#### Success Example (Status 200 OK)
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqYW5lLmRvZUBleGFtcGxlLmNvbSIsImlkIjoxLCJyb2xlIjoiVEVBQ0hFUiJ9...",
    "token_type": "bearer"
  }
}
```

#### Error Example (Status 401 Unauthorized)
```json
{
  "success": false,
  "message": "Invalid email or password"
}
```

---

### 3. Get Current User (Me)
- **Endpoint**: `GET /auth/me`
- **Purpose**: Retrieves details of the currently authenticated session owner.
- **Authentication**: JWT Bearer token required in the `Authorization` header (`Authorization: Bearer <token>`).
- **Request Body**: None.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Current user details retrieved successfully"
  - `data` (object):
    - `id` (integer): User identifier.
    - `name` (string): User's name.
    - `email` (string): User's email.
    - `role` (string): System role.

#### Success Example (Status 200 OK)
```json
{
  "success": true,
  "message": "Current user details retrieved successfully",
  "data": {
    "id": 1,
    "name": "Jane Doe",
    "email": "jane.doe@example.com",
    "role": "TEACHER"
  }
}
```

#### Error Example (Status 401 Unauthorized)
```json
{
  "success": false,
  "message": "Invalid or expired token"
}
```

---

## Exams APIs

### 1. Create Exam
- **Endpoint**: `POST /exams`
- **Purpose**: Creates a new exam configuration.
- **Authentication**: JWT Bearer token (Requires `TEACHER` or `ADMIN` role).
- **Request Body** (`application/json`):
  - `title` (string, required): Name of the exam.
  - `description` (string, optional): Context or details.
  - `max_score` (integer, required): Maximum achievable score.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Exam created successfully"
  - `data` (object):
    - `id` (integer): Unique exam identifier.
    - `title` (string): Created exam title.
    - `description` (string): Description.
    - `max_score` (integer): Max score.
    - `created_by` (integer): ID of the creator.

#### Success Example (Status 201 Created)
```json
{
  "success": true,
  "message": "Exam created successfully",
  "data": {
    "id": 10,
    "title": "Midterm Calculus",
    "description": "Calculus I Midterm Exam",
    "max_score": 100,
    "created_by": 1
  }
}
```

#### Error Example (Status 403 Forbidden)
```json
{
  "success": false,
  "message": "Access denied: insufficient permissions"
}
```

---

### 2. List Exams
- **Endpoint**: `GET /exams`
- **Purpose**: Retrieves a list of all exams accessible to the user.
- **Authentication**: JWT Bearer token (Accessible to all authenticated users).
- **Request Body**: None.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Exams retrieved successfully"
  - `data` (array of objects): Array of exam configurations.

#### Success Example (Status 200 OK)
```json
{
  "success": true,
  "message": "Exams retrieved successfully",
  "data": [
    {
      "id": 10,
      "title": "Midterm Calculus",
      "description": "Calculus I Midterm Exam",
      "max_score": 100,
      "created_by": 1
    }
  ]
}
```

---

### 3. Get Exam by ID
- **Endpoint**: `GET /exams/{id}`
- **Purpose**: Retrieves detailed information for a single exam.
- **Authentication**: JWT Bearer token.
- **Request Body**: None.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Exam details retrieved"
  - `data` (object): Detailed exam settings.

#### Success Example (Status 200 OK)
```json
{
  "success": true,
  "message": "Exam details retrieved",
  "data": {
    "id": 10,
    "title": "Midterm Calculus",
    "description": "Calculus I Midterm Exam",
    "max_score": 100,
    "created_by": 1
  }
}
```

#### Error Example (Status 404 Not Found)
```json
{
  "success": false,
  "message": "Exam with ID 10 not found"
}
```

---

### 4. Update Exam
- **Endpoint**: `PUT /exams/{id}`
- **Purpose**: Modifies an existing exam configuration.
- **Authentication**: JWT Bearer token (Requires `TEACHER` or `ADMIN` role).
- **Request Body** (`application/json`):
  - `title` (string, optional): Updated name of the exam.
  - `description` (string, optional): Updated description.
  - `max_score` (integer, optional): Updated maximum score.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Exam updated successfully"
  - `data` (object): Updated exam payload.

#### Success Example (Status 200 OK)
```json
{
  "success": true,
  "message": "Exam updated successfully",
  "data": {
    "id": 10,
    "title": "Calculus Midterm - Term 2",
    "description": "Calculus I Midterm Exam (Updated)",
    "max_score": 90,
    "created_by": 1
  }
}
```

---

### 5. Delete Exam
- **Endpoint**: `DELETE /exams/{id}`
- **Purpose**: Permanently deletes an exam.
- **Authentication**: JWT Bearer token (Requires `TEACHER` or `ADMIN` role).
- **Request Body**: None.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Exam deleted successfully"
  - `data` (object): `{}`

#### Success Example (Status 200 OK)
```json
{
  "success": true,
  "message": "Exam deleted successfully",
  "data": {}
}
```

---

## Uploads APIs

### 1. Upload Question Paper
- **Endpoint**: `POST /upload/question-paper`
- **Purpose**: Uploads the PDF/image question paper for a specific exam.
- **Authentication**: JWT Bearer token (Requires `TEACHER` or `ADMIN` role).
- **Request Body** (`multipart/form-data`):
  - `exam_id` (integer, required): ID of target exam.
  - `file` (binary, required): PDF or Image file (PNG/JPG/JPEG).
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Question paper uploaded successfully"
  - `data` (object):
    - `exam_id` (integer): ID of associated exam.
    - `file_url` (string): Accessible cloud storage URL.
    - `uploaded_at` (string): UTC timestamp.

#### Success Example (Status 201 Created)
```json
{
  "success": true,
  "message": "Question paper uploaded successfully",
  "data": {
    "exam_id": 10,
    "file_url": "https://storage.googleapis.com/grademind-question-papers/10_question_paper.pdf",
    "uploaded_at": "2026-06-11T15:10:00Z"
  }
}
```

---

### 2. Upload Answer Key
- **Endpoint**: `POST /upload/answer-key`
- **Purpose**: Uploads reference answer key or scoring rubric (PDF/Text/JSON).
- **Authentication**: JWT Bearer token (Requires `TEACHER` or `ADMIN` role).
- **Request Body** (`multipart/form-data`):
  - `exam_id` (integer, required): ID of target exam.
  - `file` (binary, required): PDF, image, or text file.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Answer key uploaded successfully"
  - `data` (object):
    - `exam_id` (integer): ID of associated exam.
    - `file_url` (string): Cloud storage URL.
    - `uploaded_at` (string): UTC timestamp.

#### Success Example (Status 201 Created)
```json
{
  "success": true,
  "message": "Answer key uploaded successfully",
  "data": {
    "exam_id": 10,
    "file_url": "https://storage.googleapis.com/grademind-answer-keys/10_answer_key.json",
    "uploaded_at": "2026-06-11T15:11:00Z"
  }
}
```

---

### 3. Upload Answer Sheet
- **Endpoint**: `POST /upload/answer-sheet`
- **Purpose**: Uploads a student's handwritten answer sheet to trigger automated evaluation.
- **Authentication**: JWT Bearer token.
- **Request Body** (`multipart/form-data`):
  - `exam_id` (integer, required): ID of target exam.
  - `student_id` (integer, required): ID of student.
  - `file` (binary, required): Handwritten answer sheet PDF/images.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Answer sheet uploaded and queued for processing"
  - `data` (object):
    - `submission_id` (integer): Unique submission ID.
    - `status` (string): "QUEUED"
    - `file_url` (string): Cloud storage URL.
    - `created_at` (string): UTC timestamp.

#### Success Example (Status 202 Accepted)
```json
{
  "success": true,
  "message": "Answer sheet uploaded and queued for processing",
  "data": {
    "submission_id": 101,
    "status": "QUEUED",
    "file_url": "https://storage.googleapis.com/grademind-answer-sheets/10_101_answer_sheet.pdf",
    "created_at": "2026-06-11T15:12:00Z"
  }
}
```

---

## Evaluation APIs

### 1. Trigger Evaluation
- **Endpoint**: `POST /evaluate/{submission_id}`
- **Purpose**: Manually forces or starts the OCR-to-Evaluation pipeline for a specific submission.
- **Authentication**: JWT Bearer token (Requires `TEACHER` or `ADMIN` role).
- **Request Body**: None.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Evaluation processing started"
  - `data` (object):
    - `submission_id` (integer): ID of processing submission.
    - `status` (string): "PROCESSING"

#### Success Example (Status 202 Accepted)
```json
{
  "success": true,
  "message": "Evaluation processing started",
  "data": {
    "submission_id": 101,
    "status": "PROCESSING"
  }
}
```

#### Error Example (Status 409 Conflict)
```json
{
  "success": false,
  "message": "Evaluation is already in progress or completed for submission 101"
}
```

---

### 2. Get Evaluation Results
- **Endpoint**: `GET /evaluation/{id}`
- **Purpose**: Returns the result of an evaluation (questions graded, scores, feedback, confidence).
- **Authentication**: JWT Bearer token.
- **Request Body**: None.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Evaluation results retrieved successfully"
  - `data` (object):
    - `id` (integer): Evaluation record ID.
    - `submission_id` (integer): Associated submission ID.
    - `total_score` (float): Accumulated graded score.
    - `status` (string): "COMPLETED" or "PENDING_REVIEW" or "FAILED".
    - `confidence_score` (float): AI confidence percentage (0.0 to 1.0).
    - `questions` (array of objects):
      - `question_number` (string): Question index.
      - `max_marks` (float): Maximum marks for this question.
      - `score_awarded` (float): Score allocated by AI.
      - `student_answer_extracted` (string): Raw text from OCR.
      - `criteria_feedback` (string): Detailed AI rubric evaluation justification.

#### Success Example (Status 200 OK)
```json
{
  "success": true,
  "message": "Evaluation results retrieved successfully",
  "data": {
    "id": 501,
    "submission_id": 101,
    "total_score": 85.5,
    "status": "COMPLETED",
    "confidence_score": 0.92,
    "questions": [
      {
        "question_number": "1a",
        "max_marks": 10.0,
        "score_awarded": 8.5,
        "student_answer_extracted": "The limit of sin(x)/x as x approaches 0 is 1 because of...",
        "criteria_feedback": "Correct reasoning. Missed listing the squeeze theorem definition explicitly, resulting in a small deduction of 1.5 marks."
      }
    ]
  }
}
```

---

## Reports & Analytics APIs

### 1. Get Report PDF
- **Endpoint**: `GET /submissions/{id}/pdf`
- **Purpose**: Downloads or redirects to the generated PDF evaluation report card.
- **Authentication**: JWT Bearer token.
- **Request Body**: None.
- **Response Body**: Binary PDF stream or Redirect (302) to Cloud Storage.

### 1a. Get Report JSON
- **Endpoint**: `GET /submissions/{id}/report`
- **Purpose**: Downloads the generated JSON evaluation report payload.
- **Authentication**: JWT Bearer token.
- **Request Body**: None.
- **Response Body**: JSON report file.

#### Success Example (Status 200 OK / 302 Found)
*Returns application/pdf content stream or redirects to GCS/S3 signed download URL.*

---

### 2. Get Exam Analytics
- **Endpoint**: `GET /analytics/exam/{exam_id}`
- **Purpose**: Returns aggregate cohort performance statistics for a specific exam.
- **Authentication**: JWT Bearer token (Requires `TEACHER` or `ADMIN` role).
- **Request Body**: None.
- **Response Body** (`application/json`):
  - `success` (boolean): `true`
  - `message` (string): "Exam analytics calculated"
  - `data` (object):
    - `exam_id` (integer): Associated exam.
    - `total_submissions` (integer): Total answer sheets evaluated.
    - `class_average` (float): Average score.
    - `highest_score` (float): Highest score in cohort.
    - `lowest_score` (float): Lowest score in cohort.
    - `distribution` (object): Score brackets distribution count.

#### Success Example (Status 200 OK)
```json
{
  "success": true,
  "message": "Exam analytics calculated",
  "data": {
    "exam_id": 10,
    "total_submissions": 45,
    "class_average": 78.4,
    "highest_score": 98.0,
    "lowest_score": 45.5,
    "distribution": {
      "90-100": 8,
      "80-89": 15,
      "70-79": 14,
      "60-69": 5,
      "below_60": 3
    }
  }
}
```
