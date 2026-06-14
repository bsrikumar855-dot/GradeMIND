/**
 * GradeMIND TypeScript Interface Definitions
 */

// ==========================================
// Authentication Types
// ==========================================
export interface User {
  id: string;
  email: string;
  name: string;
  role: 'teacher' | 'admin' | 'evaluator';
  createdAt: string;
}

export interface AuthSession {
  token: string;
  user: User;
  expiresAt: string;
}

// ==========================================
// Exam / File Upload Types
// ==========================================
export interface ExamFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'queued' | 'uploading' | 'completed' | 'failed';
  progress: number; // 0 to 100
  uploadedAt?: string;
  error?: string;
}

export interface Exam {
  id: string;
  title: string;
  subject: string;
  gradeLevel: string;
  totalQuestions: number;
  uploadedBy: string;
  uploadedAt: string;
  status: 'pending' | 'evaluating' | 'completed' | 'failed';
}

// ==========================================
// AI Evaluation Types
// ==========================================
export interface EvaluationCriteria {
  id: string;
  name: string;
  maxScore: number;
  description: string;
}

export interface QuestionResult {
  questionNumber: number;
  maxScore: number;
  scoreObtained: number;
  feedback: string;
  criteriaScores: {
    [criteriaId: string]: number;
  };
}

export interface StudentResult {
  id: string;
  studentName: string;
  rollNumber?: string;
  totalScore: number;
  maxScore: number;
  grade: string;
  questionResults: QuestionResult[];
  summaryFeedback: string;
}

export interface EvaluationJob {
  id: string;
  examId: string;
  status: 'idle' | 'processing' | 'completed' | 'failed';
  progress: number; // 0 to 100
  startedAt: string;
  completedAt?: string;
  error?: string;
  results?: StudentResult[];
}

// ==========================================
// Reports Types
// ==========================================
export interface Report {
  id: string;
  title: string;
  examId: string;
  examTitle: string;
  subject: string;
  gradeLevel: string;
  studentCount: number;
  averageScore: number;
  generatedAt: string;
  fileSize: string;
  format: 'pdf' | 'csv' | 'xlsx';
  downloadUrl: string;
}
