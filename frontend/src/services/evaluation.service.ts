import { apiClient } from './api.client';

export interface EvaluateResponse {
  success: boolean;
  message: string;
  submission_id: string;
  status: string;
}

export interface EvaluationDetailResponse {
  success: boolean;
  submission_id: string;
  exam_id: string;
  student_name: string;
  student_roll_number: string;
  status: string;
  evaluation_status: string | null;
  obtained_marks: number | null;
  total_marks: number | null;
  evaluation_confidence: number | null;
  error_message: string | null;
  evaluation_output: any;
}

export const EvaluationService = {
  evaluate: async (submissionId: string): Promise<EvaluateResponse> => {
    const response = await apiClient.post('/evaluate', { submission_id: submissionId });
    return response.data;
  },

  getEvaluation: async (submissionId: string): Promise<EvaluationDetailResponse> => {
    const response = await apiClient.get(`/evaluation/${submissionId}`);
    return response.data;
  }
};
