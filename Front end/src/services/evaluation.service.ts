import { apiClient } from './api.client';

export interface SubmissionUploadParams {
  examId: string;
  studentName: string;
  studentRollNumber: string;
  file: File;
}

export const EvaluationService = {
  /**
   * Upload a student answer sheet for evaluation - POST /submissions/upload
   * This triggers background OCR + AI evaluation on the backend.
   */
  uploadSubmission: async (params: SubmissionUploadParams) => {
    const formData = new FormData();
    formData.append('exam_id', params.examId);
    formData.append('student_name', params.studentName);
    formData.append('student_roll_number', params.studentRollNumber);
    formData.append('file', params.file);

    const response = await apiClient.post('/submissions/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return response.data;
  },

  /**
   * List submissions with optional filters - GET /submissions
   */
  listSubmissions: async (params?: {
    exam_id?: string;
    status?: string;
    skip?: number;
    limit?: number;
  }) => {
    const response = await apiClient.get('/submissions', { params });
    return response.data;
  },

  /**
   * Get full submission details - GET /submissions/{submission_id}
   */
  getSubmission: async (submissionId: string) => {
    const response = await apiClient.get(`/submissions/${submissionId}`);
    return response.data;
  },

  /**
   * Check processing status (lightweight poll) - GET /submissions/{submission_id}/status
   */
  getSubmissionStatus: async (submissionId: string) => {
    const response = await apiClient.get(`/submissions/${submissionId}/status`);
    return response.data;
  },

  /**
   * Download the evaluation report - GET /submissions/{submission_id}/report
   */
  getSubmissionReport: async (submissionId: string) => {
    const response = await apiClient.get(`/submissions/${submissionId}/report`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Delete a submission - DELETE /submissions/{submission_id}
   */
  deleteSubmission: async (submissionId: string) => {
    const response = await apiClient.delete(`/submissions/${submissionId}`);
    return response.data;
  },

  /**
   * Start evaluation for an exam by triggering backend processing.
   * This is equivalent to uploading submissions – the backend auto-starts OCR+AI.
   */
  startEvaluation: async (examId: string) => {
    // The backend triggers evaluation automatically when a submission is uploaded.
    // This method lists submissions for the exam to check current status.
    const response = await apiClient.get('/submissions', {
      params: { exam_id: examId },
    });
    return response.data;
  },

  /**
   * Get evaluation status for a specific submission (alias for getSubmissionStatus).
   */
  getEvaluationStatus: async (submissionId: string) => {
    const response = await apiClient.get(`/submissions/${submissionId}/status`);
    return response.data;
  },
};
