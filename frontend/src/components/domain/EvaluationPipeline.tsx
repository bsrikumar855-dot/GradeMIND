import * as React from "react";
import { CheckCircle, AlertTriangle, FileText, Cpu, ShieldCheck, UserCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

export interface EvaluationPipelineProps {
  submissionId: string;
  ocrConfidence?: number;
  overallConfidence?: number;
  verificationStatus?: "PASS" | "MODERATE_DISAGREEMENT" | "MAJOR_DISAGREEMENT" | "LOW_CONFIDENCE" | string;
  evaluationMode?: string;
  className?: string;
}

export function EvaluationPipeline({
  submissionId,
  ocrConfidence = 0.96,
  overallConfidence = 0.92,
  verificationStatus = "PASS",
  evaluationMode = "ANSWER_KEY",
  className,
}: EvaluationPipelineProps) {
  const isHighConfidence = overallConfidence >= 0.70;
  const isVerified = verificationStatus === "PASS";

  return (
    <div className={cn("calm-card p-5 space-y-4", className)}>
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-slate-700" />
          <h3 className="text-heading text-sm font-bold">GradeMIND Evaluation Engine Trace</h3>
        </div>
        <Badge variant="academic" className="font-mono">
          Ref: {submissionId.slice(0, 8)}
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
        <div className="p-3 rounded-md bg-slate-50 border border-slate-200/80 space-y-1">
          <span className="text-metadata text-slate-500 block">Evaluation Mode</span>
          <span className="font-bold text-slate-900 block">
            {evaluationMode === "ANSWER_KEY" ? "Rubric Matcher" : "Autonomous Evaluator"}
          </span>
          <span className="text-[11px] text-slate-500">Deterministic Value-Point</span>
        </div>

        <div className="p-3 rounded-md bg-slate-50 border border-slate-200/80 space-y-1">
          <span className="text-metadata text-slate-500 block">OCR Quality Score</span>
          <span className="font-mono font-bold text-slate-900 block">
            {Math.round(ocrConfidence * 100)}%
          </span>
          <span className="text-[11px] text-slate-500">Local TrOCR / EasyOCR</span>
        </div>

        <div className="p-3 rounded-md bg-slate-50 border border-slate-200/80 space-y-1">
          <span className="text-metadata text-slate-500 block">Verification Status</span>
          <div className="flex items-center gap-1">
            {isVerified ? (
              <>
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                <span className="font-bold text-emerald-800">Verified Pass</span>
              </>
            ) : (
              <>
                <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                <span className="font-bold text-amber-800">{verificationStatus}</span>
              </>
            )}
          </div>
          <span className="text-[11px] text-slate-500">Gemini Cross-Check</span>
        </div>

        <div className="p-3 rounded-md bg-slate-50 border border-slate-200/80 space-y-1">
          <span className="text-metadata text-slate-500 block">Operating Posture</span>
          <div className="flex items-center gap-1">
            <UserCheck className="h-3.5 w-3.5 text-blue-600" />
            <span className="font-bold text-blue-900">ASSIST-ONLY</span>
          </div>
          <span className="text-[11px] text-slate-500">Examiner Holds Authority</span>
        </div>
      </div>
    </div>
  );
}
