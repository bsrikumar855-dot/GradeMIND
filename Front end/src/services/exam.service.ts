import { apiClient } from './api.client';

export interface ExamData {
  title: string;
  subject: string;
  total_marks: number;
}

export const ExamService = {
  /**
   * List all exams - GET /exams
   */
  getExams: async () => {
    const response = await apiClient.get('/exams');
    // Backend returns { exams: [...] }
    return response.data.exams || response.data;
  },

  /**
   * Get a single exam by ID - GET /exams/{exam_id}
   */
  getExam: async (examId: string) => {
    const response = await apiClient.get(`/exams/${examId}`);
    return response.data;
  },

  /**
   * Create a new exam - POST /exams
   */
  createExam: async (examData: ExamData) => {
    const response = await apiClient.post('/exams', examData);
    return response.data;
  },

  /**
   * Update an exam - PUT /exams/{exam_id}
   */
  updateExam: async (examId: string, examData: Partial<ExamData>) => {
    const response = await apiClient.put(`/exams/${examId}`, examData);
    return response.data;
  },

  /**
   * Delete an exam - DELETE /exams/{exam_id}
   */
  deleteExam: async (examId: string) => {
    const response = await apiClient.delete(`/exams/${examId}`);
    return response.data;
  },

  /**
   * Upload an exam file with progress tracking.
   * This now creates an exam and then uploads student sheets as submissions.
   */
  uploadExamFile: async (file: File, onProgress?: (progress: number) => void) => {
    // For the upload flow, we first need to create submissions
    // The backend expects multipart form data at /submissions/upload
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post('/submissions/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
    
    return {
      id: response.data.id || response.data.data?.id || file.name,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'completed' as const,
      progress: 100,
      uploadedAt: new Date().toISOString(),
    };
  },
};
