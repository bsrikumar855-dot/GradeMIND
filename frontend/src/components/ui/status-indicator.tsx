import * as React from "react";
import { cn } from "@/utils/cn";

export type StatusType =
  | "AUTO"
  | "REVIEW"
  | "MANDATORY_HUMAN"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "PENDING_REVIEW"
  | "UPLOADED"
  | "EVALUATING"
  | string;

interface StatusIndicatorProps extends React.HTMLAttributes<HTMLSpanElement> {
  status: StatusType;
  showDot?: boolean;
}

const statusConfigs: Record<
  string,
  { label: string; bg: string; text: string; border: string; dot: string }
> = {
  AUTO: {
    label: "Auto Scored",
    bg: "bg-slate-100",
    text: "text-slate-700",
    border: "border-slate-300",
    dot: "bg-slate-500",
  },
  REVIEW: {
    label: "Review Recommended",
    bg: "bg-amber-50",
    text: "text-amber-800",
    border: "border-amber-200",
    dot: "bg-amber-500",
  },
  MANDATORY_HUMAN: {
    label: "Mandatory Review",
    bg: "bg-rose-50",
    text: "text-rose-800",
    border: "border-rose-200",
    dot: "bg-rose-500",
  },
  PENDING_REVIEW: {
    label: "Pending Examiner Review",
    bg: "bg-amber-50",
    text: "text-amber-800",
    border: "border-amber-200",
    dot: "bg-amber-500",
  },
  PROCESSING: {
    label: "Processing Engine",
    bg: "bg-blue-50",
    text: "text-blue-800",
    border: "border-blue-200",
    dot: "bg-blue-500 animate-pulse",
  },
  EVALUATING: {
    label: "Evaluating Rubric",
    bg: "bg-teal-50",
    text: "text-teal-800",
    border: "border-teal-200",
    dot: "bg-teal-500 animate-pulse",
  },
  COMPLETED: {
    label: "Evaluated",
    bg: "bg-emerald-50",
    text: "text-emerald-800",
    border: "border-emerald-200",
    dot: "bg-emerald-500",
  },
  FAILED: {
    label: "Pipeline Error",
    bg: "bg-rose-50",
    text: "text-rose-800",
    border: "border-rose-200",
    dot: "bg-rose-500",
  },
  UPLOADED: {
    label: "Uploaded",
    bg: "bg-slate-50",
    text: "text-slate-700",
    border: "border-slate-200",
    dot: "bg-slate-400",
  },
};

export function StatusIndicator({
  status,
  showDot = true,
  className,
  ...props
}: StatusIndicatorProps) {
  const config = statusConfigs[status] || {
    label: status,
    bg: "bg-slate-100",
    text: "text-slate-800",
    border: "border-slate-200",
    dot: "bg-slate-400",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-tight",
        config.bg,
        config.text,
        config.border,
        className
      )}
      {...props}
    >
      {showDot && <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />}
      {config.label}
    </span>
  );
}
