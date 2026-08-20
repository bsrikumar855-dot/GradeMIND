import * as React from "react";
import { BookOpen, Calendar, CheckCircle, FileText, Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { cn } from "@/utils/cn";

export interface AssessmentCardProps {
  id: string;
  title: string;
  subject: string;
  totalMarks: number;
  date?: string;
  evaluationMode?: "ANSWER_KEY" | "AI_AUTONOMOUS" | string;
  submissionCount?: number;
  completedCount?: number;
  reviewRequiredCount?: number;
  status?: string;
  onSelect?: (id: string) => void;
  className?: string;
}

export function AssessmentCard({
  id,
  title,
  subject,
  totalMarks,
  date,
  evaluationMode = "ANSWER_KEY",
  submissionCount = 0,
  completedCount = 0,
  reviewRequiredCount = 0,
  status = "COMPLETED",
  onSelect,
  className,
}: AssessmentCardProps) {
  return (
    <div
      className={cn(
        "calm-card calm-card-interactive p-5 flex flex-col justify-between space-y-4",
        className
      )}
    >
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <Badge variant="academic" icon={<BookOpen className="h-3 w-3" />}>
            {subject}
          </Badge>
          <StatusIndicator status={status} />
        </div>

        <h3 className="text-heading text-slate-900 font-bold line-clamp-1">{title}</h3>

        <div className="flex items-center gap-4 text-caption text-slate-500 text-xs">
          <span className="flex items-center gap-1 font-mono">
            <FileText className="h-3.5 w-3.5 text-slate-400" />
            Max: {totalMarks} Marks
          </span>
          {date && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              {date}
            </span>
          )}
        </div>
      </div>

      <div className="border-t border-slate-100 pt-3 space-y-3">
        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div className="p-2 rounded-md bg-slate-50 border border-slate-100">
            <span className="text-metadata text-slate-400 block text-[10px]">Total</span>
            <span className="font-bold text-slate-800 text-sm">{submissionCount}</span>
          </div>
          <div className="p-2 rounded-md bg-emerald-50/60 border border-emerald-100">
            <span className="text-metadata text-emerald-600 block text-[10px]">Evaluated</span>
            <span className="font-bold text-emerald-800 text-sm">{completedCount}</span>
          </div>
          <div className="p-2 rounded-md bg-amber-50/60 border border-amber-100">
            <span className="text-metadata text-amber-600 block text-[10px]">Review</span>
            <span className="font-bold text-amber-800 text-sm">{reviewRequiredCount}</span>
          </div>
        </div>

        <div className="flex items-center justify-between gap-2 pt-1">
          <Badge variant="outline" className="text-[10px] font-mono text-slate-500">
            {evaluationMode === "ANSWER_KEY" ? "Rubric Scheme Mode" : "Autonomous Mode"}
          </Badge>
          {onSelect && (
            <Button size="xs" variant="secondary" onClick={() => onSelect(id)}>
              View Examination
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
