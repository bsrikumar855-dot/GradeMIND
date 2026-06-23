import { apiClient } from './api.client';
import { EvaluationCriteria, EvaluationJob } from '@/types';

export const EvaluationService = {
  startEvaluation: async (examId: string, criteria?: EvaluationCriteria[]) => {
    void criteria;
    const response = await apiClient.post(`/evaluations/${examId}/start`);
    return response.data;
  },

  getDefaultCriteria: async () => {
    return [];
  },

  getEvaluationJobStatus: async (jobId: string) => {
    void jobId;
    return { id: jobId, examId: 'mock-exam', status: 'completed', progress: 100, startedAt: new Date().toISOString(), results: [] } as EvaluationJob;
  },

  getExamResults: async (examId: string) => {
    void examId;
    return [];
  },

  getEvaluationStatus: async (evaluationId: string) => {
    const response = await apiClient.get(`/evaluations/${evaluationId}/status`);
    return response.data;
  },

  getEvaluationById: async (id: string) => {
    void id;
    // Mock response for development
    return {
      score: 7,
      max_score: 10,
      confidence: 92,
      question: "Explain Photosynthesis",
      student_name: "John Doe",
      evaluation_date: "2026-06-18",
      concepts: [
        { name: "Definition", score: 2, max_score: 2 },
        { name: "Process", score: 3, max_score: 3 },
        { name: "Diagram", score: 1, max_score: 2 },
        { name: "Equation", score: 1, max_score: 3 }
      ],
      strengths: ["Correct Definition", "Scientific Terminology"],
      missing_concepts: ["Chemical Equation", "ATP Production"],
      suggestions: ["Add Chemical Equation", "Explain ATP Production"],
      feedback: "Strong answer but missing some important concepts."
    };
  }
};
