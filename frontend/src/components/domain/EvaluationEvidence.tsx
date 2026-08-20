import * as React from "react";
import { CheckCircle2, XCircle, FileSearch, Hash, MapPin } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

export interface CriterionEvidence {
  criterionId: string;
  description: string;
  allocatedMarks: number;
  marksAwarded: number;
  met: boolean;
  page?: number;
  characterSpan?: [number, number];
  engineVersion?: string;
}

export interface EvaluationEvidenceProps {
  rubricPoints: CriterionEvidence[];
  className?: string;
}

export function EvaluationEvidence({ rubricPoints = [], className }: EvaluationEvidenceProps) {
  return (
    <div className={cn("calm-card p-4 space-y-3", className)}>
      <div className="flex items-center justify-between border-b border-slate-100 pb-2">
        <div className="flex items-center gap-2">
          <FileSearch className="h-4 w-4 text-slate-700" />
          <h4 className="text-heading text-xs font-bold uppercase tracking-wider text-slate-900">
            Traceable Criterion Evidence
          </h4>
        </div>
        <span className="text-metadata text-[10px]">
          {rubricPoints.filter((r) => r.met).length} / {rubricPoints.length} Criteria Met
        </span>
      </div>

      <div className="space-y-2">
        {rubricPoints.map((point) => (
          <div
            key={point.criterionId}
            className={cn(
              "p-3 rounded-md border text-xs space-y-1.5 transition-colors",
              point.met
                ? "bg-emerald-50/40 border-emerald-200/80 text-emerald-950"
                : "bg-slate-50 border-slate-200 text-slate-600"
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 font-mono font-bold">
                {point.met ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-slate-400 shrink-0" />
                )}
                <span>[{point.criterionId}]</span>
                <span className="font-sans font-medium text-slate-900">{point.description}</span>
              </div>
              <Badge
                variant={point.met ? "success" : "default"}
                className="font-mono text-[11px] shrink-0"
              >
                {point.marksAwarded} / {point.allocatedMarks} Marks
              </Badge>
            </div>

            <div className="flex items-center gap-4 text-[11px] font-mono text-slate-500 pt-1 border-t border-slate-200/50">
              {point.page && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3 text-slate-400" />
                  Page {point.page}
                </span>
              )}
              {point.characterSpan && (
                <span className="flex items-center gap-1">
                  <Hash className="h-3 w-3 text-slate-400" />
                  Span [{point.characterSpan[0]}:{point.characterSpan[1]}]
                </span>
              )}
              <span className="ml-auto text-[10px] text-slate-400">
                Engine: {point.engineVersion || "GradeMIND v1.0 Deterministic"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
