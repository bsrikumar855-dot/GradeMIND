import * as React from "react";
import { Lightbulb, CheckCircle2, Target, BookOpen } from "lucide-react";
import { cn } from "@/utils/cn";

export interface AIInsightProps {
  strengths?: string[];
  weaknesses?: string[];
  improvements?: string[];
  studyRecommendations?: string[];
  summary?: string;
  className?: string;
}

export function AIInsight({
  strengths = [],
  weaknesses = [],
  improvements = [],
  studyRecommendations = [],
  summary,
  className,
}: AIInsightProps) {
  return (
    <div className={cn("calm-card p-5 space-y-4", className)}>
      <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
        <Lightbulb className="h-4 w-4 text-slate-800" />
        <h3 className="text-heading text-sm font-bold">Academic Evaluation Insights</h3>
      </div>

      {summary && (
        <p className="text-body text-xs text-slate-700 bg-slate-50 p-3 rounded border border-slate-100 leading-relaxed">
          {summary}
        </p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        {strengths.length > 0 && (
          <div className="space-y-2 p-3 rounded-md bg-emerald-50/40 border border-emerald-200/80">
            <h4 className="font-bold text-emerald-900 flex items-center gap-1.5 text-xs">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              Demonstrated Strengths
            </h4>
            <ul className="space-y-1 pl-4 list-disc text-emerald-950 text-xs">
              {strengths.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {weaknesses.length > 0 && (
          <div className="space-y-2 p-3 rounded-md bg-amber-50/40 border border-amber-200/80">
            <h4 className="font-bold text-amber-900 flex items-center gap-1.5 text-xs">
              <Target className="h-3.5 w-3.5 text-amber-600" />
              Gaps & Omissions
            </h4>
            <ul className="space-y-1 pl-4 list-disc text-amber-950 text-xs">
              {weaknesses.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {studyRecommendations.length > 0 && (
        <div className="p-3 rounded-md bg-slate-50 border border-slate-200 space-y-1.5 text-xs">
          <h4 className="font-bold text-slate-900 flex items-center gap-1.5 text-xs">
            <BookOpen className="h-3.5 w-3.5 text-slate-700" />
            Curriculum Remediation & Study Plan
          </h4>
          <div className="flex flex-wrap gap-1.5 pt-1">
            {studyRecommendations.map((topic, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded bg-white border border-slate-200 text-slate-800 text-xs font-medium shadow-2xs"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
