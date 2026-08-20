import * as React from "react";
import { Clock, CheckCircle2, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

export interface ProcessingStatusProps {
  status: "UPLOADED" | "PROCESSING" | "OCR_COMPLETE" | "EVALUATING" | "COMPLETED" | "FAILED" | string;
  errorMessage?: string;
  className?: string;
}

export function ProcessingStatus({ status, errorMessage, className }: ProcessingStatusProps) {
  const isComplete = status === "COMPLETED";
  const isFailed = status === "FAILED";
  const isProcessing = !isComplete && !isFailed;

  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      {isComplete && (
        <Badge variant="success" icon={<CheckCircle2 className="h-3 w-3" />}>
          Evaluation Completed
        </Badge>
      )}
      {isFailed && (
        <Badge variant="danger" icon={<AlertCircle className="h-3 w-3" />}>
          Processing Failed
        </Badge>
      )}
      {isProcessing && (
        <Badge variant="info" icon={<Clock className="h-3 w-3 animate-spin" />}>
          {status === "PROCESSING" ? "Running OCR..." : "Evaluating Rubric..."}
        </Badge>
      )}

      {errorMessage && (
        <span className="text-xs text-rose-600 font-medium truncate max-w-xs">{errorMessage}</span>
      )}
    </div>
  );
}
