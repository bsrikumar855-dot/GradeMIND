import { apiClient } from './api.client';

export const ReportService = {
  /**
   * Get dashboard overview metrics - GET /dashboard/overview
   * Returns: { total_exams, total_submissions, evaluated_submissions, average_score, average_confidence }
   */
  getOverview: async () => {
    const response = await apiClient.get('/dashboard/overview');
    return response.data;
  },

  /**
   * Get exam-level analytics - GET /dashboard/exams/{exam_id}
   * Returns: { exam_id, title, submission_count, average_score, top_score, lowest_score, completion_rate }
   */
  getExamAnalytics: async (examId: string) => {
    const response = await apiClient.get(`/dashboard/exams/${examId}`);
    return response.data;
  },

  /**
   * Get detailed submission review - GET /dashboard/submissions/{submission_id}
   * Returns: question breakdown, feedback, fairness checks
   */
  getSubmissionReview: async (submissionId: string) => {
    const response = await apiClient.get(`/dashboard/submissions/${submissionId}`);
    return response.data;
  },

  /**
   * Download PDF report for a submission - GET /dashboard/submissions/{submission_id}/pdf
   */
  downloadReportPdf: async (submissionId: string) => {
    const response = await apiClient.get(`/dashboard/submissions/${submissionId}/pdf`, {
      responseType: 'blob',
    });

    // Auto-trigger browser download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `report-${submissionId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Get monitoring/analytics data - GET /dashboard/monitoring
   * Returns: aggregate_analytics, score_distribution, confidence_distribution, fairness_metrics
   */
  getMonitoring: async () => {
    const response = await apiClient.get('/dashboard/monitoring');
    return response.data;
  },

  /**
   * List reports - combines submissions list with analytics for a report-style view.
   * Since the backend doesn't have a dedicated /reports endpoint, we aggregate from existing data.
   */
  listReports: async () => {
    try {
      const response = await apiClient.get('/submissions', {
        params: { status: 'COMPLETED', limit: 50 },
      });
      return response.data.submissions || [];
    } catch {
      return [];
    }
  },

  /**
   * Generate a report for an exam (download the submission report).
   */
  generateReport: async (examId: string, _format: string = 'pdf') => {
    // List completed submissions for this exam
    const response = await apiClient.get('/submissions', {
      params: { exam_id: examId, status: 'COMPLETED' },
    });
    const submissions = response.data.submissions || [];
    if (submissions.length > 0) {
      return submissions[0]; // Return the first completed submission
    }
    throw new Error('No completed submissions found for this exam.');
  },

  /**
   * Download a report by submission ID.
   */
  downloadReport: async (submissionId: string) => {
    // Return the URL for the report endpoint
    return `${apiClient.defaults.baseURL}/dashboard/submissions/${submissionId}/pdf`;
  },
};
