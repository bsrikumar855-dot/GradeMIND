"use client";

import * as React from "react";
import { ReportService } from "@/services/report.service";

interface DashboardOverview {
  total_exams: number;
  total_submissions: number;
  evaluated_submissions: number;
  average_score: number;
  average_confidence: number;
}

interface MonitoringData {
  aggregate_analytics: {
    total_submissions: number;
    completed_submissions: number;
    failed_submissions: number;
    average_score: number;
    average_confidence: number;
  };
  score_distribution: Record<string, number>;
  confidence_distribution: Record<string, number>;
  fairness_metrics: {
    average_fairness_score: number;
    bias_free_rate: number;
    flagged_submissions_count: number;
  };
}

interface ReportsState {
  overview: DashboardOverview | null;
  monitoring: MonitoringData | null;
  completedSubmissions: unknown[];
  isLoading: boolean;
  error: string | null;
}

interface ReportsContextType extends ReportsState {
  loadOverview: () => Promise<void>;
  loadMonitoring: () => Promise<void>;
  loadCompletedSubmissions: () => Promise<void>;
  downloadPdf: (submissionId: string) => Promise<void>;
  getExamAnalytics: (examId: string) => Promise<unknown>;
  getSubmissionReview: (submissionId: string) => Promise<unknown>;
  clearReportsError: () => void;
}

const ReportsContext = React.createContext<ReportsContextType | undefined>(undefined);

export const ReportsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = React.useState<ReportsState>({
    overview: null,
    monitoring: null,
    completedSubmissions: [],
    isLoading: false,
    error: null,
  });

  const loadOverview = async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const overview = await ReportService.getOverview();
      setState((prev) => ({ ...prev, overview, isLoading: false }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load overview.",
      }));
    }
  };

  const loadMonitoring = async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const monitoring = await ReportService.getMonitoring();
      setState((prev) => ({ ...prev, monitoring, isLoading: false }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load monitoring data.",
      }));
    }
  };

  const loadCompletedSubmissions = async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const submissions = await ReportService.listReports();
      setState((prev) => ({ ...prev, completedSubmissions: submissions, isLoading: false }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: err instanceof Error ? err.message : "Failed to load submissions.",
      }));
    }
  };

  const downloadPdf = async (submissionId: string) => {
    try {
      await ReportService.downloadReportPdf(submissionId);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Failed to download report.",
      }));
    }
  };

  const getExamAnalytics = async (examId: string) => {
    try {
      return await ReportService.getExamAnalytics(examId);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Failed to load exam analytics.",
      }));
      return null;
    }
  };

  const getSubmissionReview = async (submissionId: string) => {
    try {
      return await ReportService.getSubmissionReview(submissionId);
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Failed to load submission review.",
      }));
      return null;
    }
  };

  const clearReportsError = () => {
    setState((prev) => ({ ...prev, error: null }));
  };

  return (
    <ReportsContext.Provider
      value={{
        ...state,
        loadOverview,
        loadMonitoring,
        loadCompletedSubmissions,
        downloadPdf,
        getExamAnalytics,
        getSubmissionReview,
        clearReportsError,
      }}
    >
      {children}
    </ReportsContext.Provider>
  );
};

export const useReports = () => {
  const context = React.useContext(ReportsContext);
  if (context === undefined) {
    throw new Error("useReports must be used within a ReportsProvider");
  }
  return context;
};
