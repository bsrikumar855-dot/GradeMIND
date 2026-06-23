import { apiClient } from './api.client';

export const ReportService = {
  listReports: async (filters?: Record<string, unknown>) => {
    const response = await apiClient.get('/reports', { params: filters });
    return response.data;
  },

  downloadReportPdf: async (reportId: string) => {
    const response = await apiClient.get(`/reports/${reportId}/download`, {
      responseType: 'blob'
    });
    
    // Auto-trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `report-${reportId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
  },

  generateReport: async (examId: string, format: string) => {
    const response = await apiClient.post(`/reports/generate`, { examId, format });
    return response.data;
  },

  downloadReport: async (reportId: string) => {
    void reportId;
    return `/api/reports/${reportId}/download`;
  }
};
