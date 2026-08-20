import * as React from "react";
import { LoadingSpinner } from "./loading-spinner";
import { cn } from "@/utils/cn";

interface LoadingStateProps extends React.HTMLAttributes<HTMLDivElement> {
  message?: string;
  caption?: string;
}

export function LoadingState({
  message = "Loading evaluation data...",
  caption = "GradeMIND AI Examination Engine",
  className,
  ...props
}: LoadingStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-12 text-center calm-card bg-white min-h-[220px]",
        className
      )}
      {...props}
    >
      <LoadingSpinner size="lg" className="text-slate-800 mb-4" />
      <p className="text-sm font-semibold text-slate-800 tracking-tight">{message}</p>
      {caption && <p className="text-metadata text-slate-400 mt-1">{caption}</p>}
    </div>
  );
}
