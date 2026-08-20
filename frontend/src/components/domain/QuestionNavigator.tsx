import * as React from "react";
import { CheckCircle2, AlertCircle, HelpCircle } from "lucide-react";
import { cn } from "@/utils/cn";

export interface QuestionTabItem {
  questionNumber: string;
  maxMarks: number;
  scoreAwarded?: number;
  confidence?: number;
  reviewRequired?: boolean;
}

export interface QuestionNavigatorProps {
  questions: QuestionTabItem[];
  activeIndex: number;
  onSelect: (index: number) => void;
  className?: string;
}

export function QuestionNavigator({
  questions = [],
  activeIndex,
  onSelect,
  className,
}: QuestionNavigatorProps) {
  return (
    <div className={cn("flex items-center gap-1.5 overflow-x-auto pb-1.5 pt-0.5", className)}>
      {questions.map((q, idx) => {
        const isActive = idx === activeIndex;
        const isReviewed = q.reviewRequired;
        const isScored = q.scoreAwarded !== undefined;

        return (
          <button
            key={q.questionNumber}
            onClick={() => onSelect(idx)}
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-medium transition-all shrink-0 cursor-pointer",
              isActive
                ? "bg-slate-900 text-white border-slate-900 shadow-xs"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50 hover:border-slate-300",
              isReviewed && !isActive && "border-amber-300 bg-amber-50/50 text-amber-900"
            )}
          >
            <span className="font-mono font-bold">Q{q.questionNumber}</span>
            {isScored && (
              <span
                className={cn(
                  "font-mono text-[11px] px-1.5 py-0.2 rounded",
                  isActive ? "bg-slate-800 text-slate-200" : "bg-slate-100 text-slate-700"
                )}
              >
                {q.scoreAwarded}/{q.maxMarks}
              </span>
            )}
            {isReviewed && <AlertCircle className="h-3 w-3 text-amber-500 shrink-0" />}
          </button>
        );
      })}
    </div>
  );
}
