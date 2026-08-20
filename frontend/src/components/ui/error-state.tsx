import * as React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "./button";
import { cn } from "@/utils/cn";

interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  message?: string;
  onRetry?: () => void;
  retryText?: string;
}

export function ErrorState({
  title = "Evaluation Processing Error",
  message = "An unexpected error occurred while communicating with the GradeMIND evaluation server. Please retry.",
  onRetry,
  retryText = "Retry Operation",
  className,
  ...props
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center rounded-lg border border-rose-200 bg-rose-50/50 calm-card",
        className
      )}
      {...props}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600 mb-3">
        <AlertCircle className="h-6 w-6" />
      </div>
      <h3 className="text-heading text-rose-950 mb-1">{title}</h3>
      <p className="text-body text-rose-800/90 max-w-md mb-4">{message}</p>
      {onRetry && (
        <Button
          variant="danger"
          size="sm"
          onClick={onRetry}
          leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
        >
          {retryText}
        </Button>
      )}
    </div>
  );
}
