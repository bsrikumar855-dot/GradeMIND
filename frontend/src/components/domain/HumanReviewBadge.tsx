import * as React from "react";
import { UserCheck, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

export interface HumanReviewBadgeProps {
  requiresReview?: boolean;
  reason?: string;
  className?: string;
}

export function HumanReviewBadge({
  requiresReview = true,
  reason = "ASSIST-ONLY mode routes all evaluations for examiner sign-off.",
  className,
}: HumanReviewBadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium",
        requiresReview
          ? "bg-amber-50 border-amber-200 text-amber-900"
          : "bg-slate-50 border-slate-200 text-slate-700",
        className
      )}
    >
      {requiresReview ? (
        <ShieldAlert className="h-4 w-4 text-amber-600 shrink-0" />
      ) : (
        <UserCheck className="h-4 w-4 text-slate-600 shrink-0" />
      )}
      <div>
        <span className="font-bold block">
          {requiresReview ? "Examiner Confirmation Required" : "Examiner Sign-Off Completed"}
        </span>
        {reason && <span className="text-[11px] opacity-85 block">{reason}</span>}
      </div>
    </div>
  );
}
