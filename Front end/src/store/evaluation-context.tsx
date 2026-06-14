"use client";

import * as React from "react";
import { EvaluationService } from "@/services/evaluation.service";

interface Submission {
  id: string;
  exam_id: string;
  student_name: string;
  student_roll_number: string;
  status: string;
  ocr_status?: string;
  evaluation_status?: string;
  obtained_marks?: number;
  total_marks?: number;
  ocr_confidence?: number;
  evaluation_confidence?: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

interface EvaluationState {
  submissions: Submission[];
  currentSubmission: Submission | null;
  isEvaluating: boolean;
  isLoading: boolean;
  error: string | null;
  totalCount: number;
}

interface EvaluationContextType extends EvaluationState {
  uploadSubmission: (params: {
    examId: string;
    studentName: string;
    studentRollNumber: string;
    file: File;
  }) => Promise<void>;
  fetchSubmissions: (examId?: string) => Promise<void>;
  fetchSubmissionStatus: (submissionId: string) => Promise<void>;
  clearEvaluationState: () => void;
}

const EvaluationContext = React.createContext<EvaluationContextType | undefined>(undefined);

export const EvaluationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = React.useState<EvaluationState>({
    submissions: [],
    currentSubmission: null,
    isEvaluating: false,
    isLoading: false,
    error: null,
    totalCount: 0,
  });

  const uploadSubmission = async (params: {
    examId: string;
    studentName: string;
    studentRollNumber: string;
    file: File;
  }) => {
    setState((prev) => ({ ...prev, isEvaluating: true, error: null }));
    try {
      const result = await EvaluationService.uploadSubmission(params);
      setState((prev) => ({
        ...prev,
        currentSubmission: result,
        submissions: [result, ...prev.submissions],
        isEvaluating: false,
      }));
    } catch (err: unknown) {
      let errorMessage = "Failed to upload submission.";
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string } } };
        errorMessage = axiosError.response?.data?.detail || errorMessage;
      }
      setState((prev) => ({
        ...prev,
        isEvaluating: false,
        error: errorMessage,
      }));
      throw err;
    }
  };

  const fetchSubmissions = async (examId?: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await EvaluationService.listSubmissions(
        examId ? { exam_id: examId } : undefined
      );
      setState((prev) => ({
        ...prev,
        submissions: result.submissions || [],
        totalCount: result.total || 0,
        isLoading: false,
      }));
    } catch (err: unknown) {
      let errorMessage = "Failed to fetch submissions.";
      if (err instanceof Error) {
        errorMessage = err.message;
      }
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
    }
  };

  const fetchSubmissionStatus = async (submissionId: string) => {
    try {
      const status = await EvaluationService.getSubmissionStatus(submissionId);
      setState((prev) => ({
        ...prev,
        currentSubmission: status,
        submissions: prev.submissions.map((s) =>
          s.id === submissionId ? { ...s, ...status } : s
        ),
        isEvaluating: status.status === 'PROCESSING' || status.status === 'EVALUATING',
      }));
    } catch (err: unknown) {
      let errorMessage = "Failed to check submission status.";
      if (err instanceof Error) {
        errorMessage = err.message;
      }
      setState((prev) => ({
        ...prev,
        error: errorMessage,
      }));
    }
  };

  const clearEvaluationState = () => {
    setState({
      submissions: [],
      currentSubmission: null,
      isEvaluating: false,
      isLoading: false,
      error: null,
      totalCount: 0,
    });
  };

  return (
    <EvaluationContext.Provider
      value={{
        ...state,
        uploadSubmission,
        fetchSubmissions,
        fetchSubmissionStatus,
        clearEvaluationState,
      }}
    >
      {children}
    </EvaluationContext.Provider>
  );
};

export const useEvaluation = () => {
  const context = React.useContext(EvaluationContext);
  if (context === undefined) {
    throw new Error("useEvaluation must be used within an EvaluationProvider");
  }
  return context;
};
