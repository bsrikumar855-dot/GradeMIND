
<h1 align="center">🧠 GradeMIND</h1>

<h3 align="center">
AI-Powered Autonomous Answer Sheet Evaluation Platform
</h3>

<p align="center">

<img src="https://readme-typing-svg.herokuapp.com?font=Poppins&weight=700&size=24&duration=3000&pause=1000&color=2E8B57&center=true&vCenter=true&width=700&lines=AI-Powered+Answer+Sheet+Evaluation;Autonomous+Academic+Assessment;Instant+Feedback+Generation;OCR+%2B+LLM+%2B+Analytics;Built+for+the+Future+of+Education"/>

</p>

<p align="center">

<img src="https://img.shields.io/github/stars/bsrikumar855-dot/GradeMIND?style=for-the-badge"/>
<img src="https://img.shields.io/github/forks/bsrikumar855-dot/GradeMIND?style=for-the-badge"/>
<img src="https://img.shields.io/github/license/bsrikumar855-dot/GradeMIND?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge"/>

</p>

---

# 🎯 Problem Statement

Traditional answer sheet evaluation suffers from:

❌ Time-consuming manual grading

❌ Human bias and inconsistency

❌ Delayed student feedback

❌ Lack of learning analytics

❌ Difficulty handling large-scale examinations

❌ No personalized improvement guidance

---

# 💡 Solution

GradeMIND introduces an AI-driven autonomous evaluation ecosystem that:

✅ Extracts handwritten answers using OCR

✅ Understands question intent using AI

✅ Evaluates answers semantically

✅ Awards marks automatically

✅ Generates detailed feedback

✅ Identifies strengths & weaknesses

✅ Creates personalized study plans

✅ Produces professional reports instantly

---

# 🏗 System Architecture

```mermaid
flowchart LR

A[Question Paper] --> B[Exam Creation]
B --> C[Student Submission]

C --> D[OCR Engine]
D --> E[Question Understanding]

E --> F[Semantic Evaluation Engine]

F --> G[Mark Allocation]
F --> H[Concept Coverage Analysis]
F --> I[Feedback Generation]

G --> J[Analytics Engine]

H --> J
I --> J

J --> K[Student Report]
J --> L[Teacher Dashboard]
J --> M[Institution Analytics]
```

---

# ⚡ Core Features

## 📄 Smart Exam Management

- Create Exams
- Publish Exams
- Manage Questions
- Configure Marks
- Multiple Subjects

---

## 📝 Answer Sheet Upload

- PDF Upload
- JPG Upload
- PNG Upload
- Multi-page Support
- OCR Ready

---

## 🤖 Autonomous Evaluation

- AI-based Grading
- Semantic Similarity
- Concept Coverage
- Intelligent Marking
- Confidence Scoring

---

## 📊 Advanced Analytics

- Class Performance
- Accuracy Distribution
- Score Trends
- Evaluation Statistics
- Performance Insights

---

## 🎯 Personalized Feedback

- Strength Analysis
- Weakness Detection
- Action Plans
- Topic Recommendations
- Practice Suggestions

---

## 📑 Professional Report Generation

- Student Reports
- Evaluation Breakdown
- Visual Analytics
- Study Recommendations
- Downloadable PDF

---

# 🧠 AI Evaluation Pipeline

```mermaid
flowchart TD

A[Question] --> B[Question Understanding]

C[Student Answer] --> D[OCR Extraction]

B --> E[Concept Extraction]
D --> F[Semantic Processing]

E --> G[Evaluation Layer]
F --> G

G --> H[Mark Calculation]

G --> I[Strength Analysis]

G --> J[Weakness Analysis]

H --> K[Final Report]
I --> K
J --> K
```

---

# 🛠 Technology Stack

## Frontend

```yaml
Next.js 14
TypeScript
Tailwind CSS
Framer Motion
Recharts
React Hook Form
```

## Backend

```yaml
FastAPI
Python
SQLAlchemy
Alembic
PostgreSQL
JWT Authentication
```

## AI Layer

```yaml
Google Gemini
OCR Engine
Semantic Evaluation
Question Understanding
Feedback Generation
```

## Infrastructure

```yaml
Docker
GitHub
Vercel
PostgreSQL
```

---

# 📂 Project Structure

```bash
GradeMIND
│
├── frontend/
│   ├── src/
│   ├── app/
│   ├── components/
│   └── services/
│
├── backend/
│   ├── app/
│   ├── api/
│   ├── models/
│   ├── services/
│   ├── schemas/
│   └── alembic/
│
├── AI/
│   ├── evaluation/
│   ├── prompts/
│   └── testing/
│
└── docs/
```

---

# 🚀 End-to-End Workflow

```mermaid
sequenceDiagram

Teacher->>GradeMIND: Create Exam

Teacher->>GradeMIND: Publish Exam

Student->>GradeMIND: Upload Answer Sheet

GradeMIND->>OCR Engine: Extract Text

OCR Engine->>AI Evaluator: Send Answers

AI Evaluator->>GradeMIND: Evaluate

GradeMIND->>Analytics Engine: Process Results

Analytics Engine->>Student: Personalized Feedback

Analytics Engine->>Teacher: Performance Dashboard
```

---

# 📈 Key Metrics

| Metric | Achievement |
|----------|------------|
| Evaluation Time | < 10 sec |
| Automated Grading | 100% |
| AI Feedback | Real-time |
| OCR Support | PDF/JPG/PNG |
| Personalized Reports | Yes |
| Dashboard Analytics | Yes |

---

# 🌟 Unique Innovations

### Autonomous Evaluation Engine

Evaluates answers without requiring exact keyword matches.

### Concept Coverage Analysis

Measures conceptual understanding rather than memorization.

### Personalized Learning Reports

Each student receives targeted improvement recommendations.

### AI-Powered Insights

Identifies patterns invisible to manual evaluation.

### Teacher Analytics

Class-wide performance intelligence.

---

# 👥 Team GradeMIND

| Member | Role |
|----------|------|
| Shree Kumar | System Architecture & AI |
| Nakshatra | Backend Development |
| Vishwanath | AI Evaluation Pipeline |
| Meena | Frontend Development |

---

# 📸 Product Preview

Add screenshots:

```md
## Dashboard

![Dashboard](./assets/dashboard.png)

## Evaluation Report

![Report](./assets/report.png)

## Analytics

![Analytics](./assets/analytics.png)
```

---

# 🏆 Future Roadmap

- Voice Answer Evaluation
- Multilingual Evaluation
- Adaptive Learning Engine
- AI Question Generation
- Plagiarism Detection
- Real-time Exam Monitoring
- Mobile Application
- Institution-wide Analytics

---

# ⭐ Support GradeMIND

If you found this project useful:

🌟 Star the repository

🍴 Fork the repository

🚀 Contribute to development

📢 Share with educators

---

<h3 align="center">

Built with ❤️ by Team GradeMIND

"Transforming Evaluation Through Artificial Intelligence"

</h3>
# 🚀 Installation & Setup Guide

## 📋 Prerequisites

Make sure you have installed:

```bash
Node.js >= 18
Python >= 3.11
PostgreSQL >= 15
Git
```

---

# 📥 Clone Repository

```bash
git clone https://github.com/bsrikumar855-dot/GradeMIND.git

cd GradeMIND
```

---

# 🗄 Database Setup

Create PostgreSQL Database

```sql
CREATE DATABASE grademind;
```

Update backend `.env`

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/grademind

GEMINI_API_KEY=YOUR_API_KEY

SECRET_KEY=super_secret_key

ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

# ⚙ Backend Setup

Navigate to backend:

```bash
cd backend
```

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
alembic upgrade head
```

Start FastAPI Server:

```bash
uvicorn app.main:app --reload
```

Backend runs at:

```bash
http://localhost:8000
```

Swagger Docs:

```bash
http://localhost:8000/docs
```

---

# 🎨 Frontend Setup

Open new terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Configure frontend environment:

`.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run frontend:

```bash
npm run dev
```

Frontend runs at:

```bash
http://localhost:3000
```

---

# 🤖 AI Configuration

Generate Gemini API Key:

https://aistudio.google.com

Add key inside:

```env
GEMINI_API_KEY=YOUR_API_KEY
```

GradeMIND uses Gemini for:

- Question Understanding
- Semantic Evaluation
- Feedback Generation
- Report Generation
- Concept Coverage Analysis

---

# 🧪 Test the System

## Step 1

Create an Exam

```text
Upload Exam → Publish Exam
```

## Step 2

Upload Student Answer Sheet

```text
AI Evaluation → Upload Sheet
```

Supported:

- PDF
- JPG
- PNG

---

## Step 3

Run Evaluation

```text
Evaluate → Generate Results
```

---

## Step 4

View Reports

```text
Results Dashboard
Teacher Feedback
Analytics Reports
```

---

# 📊 API Documentation

Once backend is running:

```bash
http://localhost:8000/docs
```

Available APIs:

```yaml
Authentication
Exam Management
Student Management
Submission Upload
AI Evaluation
Results
Reports
Analytics
```

---

# 🐳 Docker Setup (Optional)

Build Containers:

```bash
docker-compose build
```

Run Containers:

```bash
docker-compose up
```

Stop Containers:

```bash
docker-compose down
```

---

# 🔍 Common Troubleshooting

### Database Connection Error

```bash
Check PostgreSQL is running
Check DATABASE_URL
```

---

### Gemini API Error

```bash
Verify GEMINI_API_KEY
Restart backend
```

---

### Frontend Cannot Connect

```bash
Check NEXT_PUBLIC_API_URL
Verify backend running on :8000
```

---

### Migration Issues

```bash
alembic downgrade base

alembic upgrade head
```

---

# ✅ Verification Checklist

- [ ] PostgreSQL Connected
- [ ] Backend Running
- [ ] Frontend Running
- [ ] Gemini API Configured
- [ ] Exam Created
- [ ] Submission Uploaded
- [ ] Evaluation Completed
- [ ] Report Generated
- [ ] Analytics Dashboard Working
