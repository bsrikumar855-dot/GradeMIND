import { apiClient } from './api.client';

export interface ReportResponse {
  success: boolean;
  report: any;
}

export interface StudentScore {
  submission_id: string;
  student_name: string;
  student_roll_number: string;
  obtained_marks: number | null;
  total_marks: number | null;
  status: string;
}

export interface ClassAnalyticsResponse {
  success: boolean;
  exam_id: string;
  exam_title: string;
  subject: string;
  total_marks: number;
  total_submissions: number;
  completed_submissions: number;
  average_score: number | null;
  top_score: number | null;
  lowest_score: number | null;
  completion_rate: number | null;
  pass_rate: number;
  score_distribution: {
    "90-100": number;
    "80-89": number;
    "70-79": number;
    "60-69": number;
    "below_60": number;
  };
  student_scores: StudentScore[];
}

export const ReportService = {
  getReport: async (submissionId: string): Promise<ReportResponse> => {
    const response = await apiClient.get(`/reports/${submissionId}`);
    return response.data;
  },

  getClassAnalytics: async (examId: string): Promise<ClassAnalyticsResponse> => {
    const response = await apiClient.get(`/analytics/class/${examId}`);
    return response.data;
  }
};
