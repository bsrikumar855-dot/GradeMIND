import * as React from "react";
import { Info } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

export interface ConceptCoverageProps {
  coveragePercentage: number;
  matchedConcepts?: string[];
  missingConcepts?: string[];
  className?: string;
}

export function ConceptCoverage({
  coveragePercentage,
  matchedConcepts = [],
  missingConcepts = [],
  className,
}: ConceptCoverageProps) {
  const percentage = Math.round(coveragePercentage);

  return (
    <div className={cn("calm-card p-4 space-y-3", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="text-heading text-xs font-bold uppercase tracking-wider text-slate-700">
            Concept Extraction Coverage
          </h4>
          <Badge variant="academic" className="text-[10px]">
            Display Only
          </Badge>
        </div>
        <span className="font-mono text-xs font-bold text-slate-900">{percentage}%</span>
      </div>

      <Progress value={percentage} indicatorClassName="bg-teal-600" />

      <div className="flex items-start gap-1.5 text-[11px] text-slate-500 bg-slate-50 p-2 rounded border border-slate-100">
        <Info className="h-3.5 w-3.5 text-slate-400 shrink-0 mt-0.5" />
        <p>
          Concept coverage provides observational topic diagnostics. Per GradeMIND architecture, numeric marks are awarded strictly by deterministic rubric criteria matching.
        </p>
      </div>

      {(matchedConcepts.length > 0 || missingConcepts.length > 0) && (
        <div className="grid grid-cols-2 gap-3 pt-1 text-xs">
          <div>
            <span className="text-metadata text-[10px] text-emerald-700 block mb-1">
              Detected Key Concepts ({matchedConcepts.length})
            </span>
            <div className="flex flex-wrap gap-1">
              {matchedConcepts.map((c, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-900 border border-emerald-200 text-[11px] font-medium"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>

          <div>
            <span className="text-metadata text-[10px] text-slate-500 block mb-1">
              Unmatched Concepts ({missingConcepts.length})
            </span>
            <div className="flex flex-wrap gap-1">
              {missingConcepts.map((c, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 text-[11px]"
                >
                  {c}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
