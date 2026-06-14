"use client";

import * as React from "react";
import { AuthProvider } from "./auth-context";
import { UploadProvider } from "./upload-context";
import { EvaluationProvider } from "./evaluation-context";
import { ReportsProvider } from "./reports-context";

export interface StoreProviderProps {
  children: React.ReactNode;
}

export const StoreProvider: React.FC<StoreProviderProps> = ({ children }) => {
  return (
    <AuthProvider>
      <UploadProvider>
        <EvaluationProvider>
          <ReportsProvider>
            {children}
          </ReportsProvider>
        </EvaluationProvider>
      </UploadProvider>
    </AuthProvider>
  );
};
