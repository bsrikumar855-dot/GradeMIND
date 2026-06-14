"use client";

import * as React from "react";
import { ExamFile } from "@/types";
import { ExamService } from "@/services/exam.service";

interface UploadState {
  files: ExamFile[];
  isUploading: boolean;
  error: string | null;
}

interface UploadContextType extends UploadState {
  uploadFile: (file: File) => Promise<void>;
  removeFile: (id: string) => void;
  clearQueue: () => void;
}

const UploadContext = React.createContext<UploadContextType | undefined>(undefined);

export const UploadProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = React.useState<UploadState>({
    files: [],
    isUploading: false,
    error: null,
  });

  const uploadFile = async (file: File) => {
    const tempId = `temp_${Math.random().toString(36).substring(7)}`;
    const newFileItem: ExamFile = {
      id: tempId,
      name: file.name,
      size: file.size,
      type: file.type,
      status: "uploading",
      progress: 0,
    };

    setState((prev) => ({
      ...prev,
      files: [...prev.files, newFileItem],
      isUploading: true,
      error: null,
    }));

    try {
      const completedItem = await ExamService.uploadExamFile(file, (progress) => {
        setState((prev) => ({
          ...prev,
          files: prev.files.map((f) => (f.id === tempId ? { ...f, progress } : f)),
        }));
      });

      setState((prev) => {
        const updatedFiles = prev.files.map((f) => (f.id === tempId ? completedItem : f));
        const stillUploading = updatedFiles.some((f) => f.status === "uploading");
        return {
          ...prev,
          files: updatedFiles,
          isUploading: stillUploading,
        };
      });
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Upload failed.";
      setState((prev) => {
        const updatedFiles = prev.files.map((f) =>
          f.id === tempId ? { ...f, status: "failed" as const, error: errMsg } : f
        );
        const stillUploading = updatedFiles.some((f) => f.status === "uploading");
        return {
          ...prev,
          files: updatedFiles,
          isUploading: stillUploading,
          error: errMsg,
        };
      });
      throw err;
    }
  };

  const removeFile = (id: string) => {
    setState((prev) => {
      const updatedFiles = prev.files.filter((f) => f.id !== id);
      const stillUploading = updatedFiles.some((f) => f.status === "uploading");
      return {
        ...prev,
        files: updatedFiles,
        isUploading: stillUploading,
      };
    });
  };

  const clearQueue = () => {
    setState({
      files: [],
      isUploading: false,
      error: null,
    });
  };

  return (
    <UploadContext.Provider value={{ ...state, uploadFile, removeFile, clearQueue }}>
      {children}
    </UploadContext.Provider>
  );
};

export const useUpload = () => {
  const context = React.useContext(UploadContext);
  if (context === undefined) {
    throw new Error("useUpload must be used within an UploadProvider");
  }
  return context;
};
