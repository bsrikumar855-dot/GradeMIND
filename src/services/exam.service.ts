import { apiClient } from './api.client';
import { ExamFile } from '@/types';

export const ExamService = {
  getExams: async () => {
    const response = await apiClient.get('/exams');
    return response.data;
  },
  
  uploadExam: async (formData: FormData) => {
    const response = await apiClient.post('/exams/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  uploadExamFile: async (file: File, onProgress?: (progress: number) => void) => {
    if (onProgress) onProgress(100);
    return { id: 'mock-exam', name: file.name, status: 'completed', size: file.size, type: file.type, progress: 100 } as ExamFile;
  }
};
