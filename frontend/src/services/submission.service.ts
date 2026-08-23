import { apiClient } from './api.client';

export interface UploadSubmissionData {
  exam_id: string;
  student_name: string;
  student_roll_number: string;
  file: File;
}

export const SubmissionService = {
  upload: async (data: UploadSubmissionData) => {
    const formData = new FormData();
    formData.append('exam_id', data.exam_id);
    formData.append('student_name', data.student_name);
    formData.append('student_roll_number', data.student_roll_number);
    formData.append('file', data.file);

    const response = await apiClient.post('/submissions/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return {
      success: true,
      data: response.data,
      ...response.data
    };
  },

  getSubmissions: async (params?: { exam_id?: string; status?: string; skip?: number; limit?: number }) => {
    const response = await apiClient.get('/submissions', { params });
    return {
      success: true,
      data: response.data
    };
  },

  getEvaluatedSubmissions: async () => {
    let v1List = [];
    try {
      const response = await apiClient.get('/submissions', {
        params: { status: 'COMPLETED', limit: 100 }
      });
      v1List = Array.isArray(response.data?.submissions)
        ? response.data.submissions
        : (Array.isArray(response.data) ? response.data : []);
    } catch (e) {
      console.warn("Failed to fetch V1 submissions", e);
    }

    let v2List = [];
    try {
      const v2Res = await apiClient.get('/api/v2/jobs');
      if (Array.isArray(v2Res.data)) {
         v2List = v2Res.data;
      }
    } catch (e) {
      console.warn("Failed to fetch V2 jobs", e);
    }

    return {
      success: true,
      data: [...v2List, ...v1List]
    };
  },

  getSubmissionById: async (submissionId: string) => {
    const response = await apiClient.get(`/submissions/${submissionId}`);
    return {
      success: true,
      data: response.data
    };
  },

  getStatus: async (submissionId: string) => {
    const response = await apiClient.get(`/submissions/${submissionId}/status`);
    return {
      success: true,
      data: response.data
    };
  },

  getReport: async (submissionId: string) => {
    // 1. Try V2 job report first
    try {
      const v2Res = await apiClient.get(`/api/v2/grade/${submissionId}`);
      if (v2Res.data && v2Res.data.report) {
         return {
           success: true,
           data: {
              evaluation_summary: v2Res.data.report.evaluation_summary,
              student_dashboard: { subject: "Demo Subject", recent_exams: [] },
              teacher_dashboard: {},
              metadata: {
                version: "v2",
                student_name: v2Res.data.report.student?.name || `Demo Student (${submissionId.slice(0, 6)})`,
                student_roll_number: v2Res.data.report.student?.roll_number || submissionId.slice(0, 8)
              },
              report: v2Res.data.report,
              results: v2Res.data.report.questions,
              totals: v2Res.data.report.totals,
              coverage: v2Res.data.report.coverage
           }
         };
      }
    } catch (v2e) {
      // Ignore V2 error and try V1 submission report endpoint
    }

    // 2. Try V1 submission report endpoint
    try {
      const response = await apiClient.get(`/submissions/${submissionId}/report`);
      return {
        success: true,
        data: response.data
      };
    } catch (e: any) {
      console.error("Failed to retrieve submission report:", e);
      return { success: false, data: null };
    }
  },

  getPdf: async (submissionId: string) => {
    const response = await apiClient.get(`/submissions/${submissionId}/pdf`, {
      responseType: 'blob'
    });
    return response.data;
  },

  deleteSubmission: async (submissionId: string) => {
    const response = await apiClient.delete(`/submissions/${submissionId}`);
    return {
      success: true,
      data: response.data,
      ...response.data
    };
  },

  gradeV2: async (paper: File, answers: File, scheme: File, mask?: string, maxPages?: number, offline?: boolean) => {
    const formData = new FormData();
    formData.append('paper', paper);
    formData.append('answers', answers);
    formData.append('scheme', scheme);
    if (mask) formData.append('mask', mask);
    if (maxPages) formData.append('max_pages', maxPages.toString());
    if (offline !== undefined) formData.append('offline', offline ? 'true' : 'false');

    const response = await apiClient.post('/api/v2/grade', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data; // { job_id: '...', status: 'accepted' }
  },

  pollGradeJob: async (jobId: string) => {
    const response = await apiClient.get(`/api/v2/grade/${jobId}`);
    return response.data; // { status: 'running' | 'completed' | 'failed', report: ... }
  }
};
