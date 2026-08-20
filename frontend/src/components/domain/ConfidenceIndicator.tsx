import * as React from "react";
import { AlertCircle, HelpCircle, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/utils/cn";

export interface ConfidenceBreakdown {
  ocr_confidence?: number;
  explainability_score?: number;
  semantic_alignment_score?: number;
  fairness_score?: number;
  concept_coverage_score?: number;
}

export interface ConfidenceIndicatorProps {
  confidence: number;
  breakdown?: ConfidenceBreakdown;
  isCalibrated?: boolean;
  className?: string;
}

export function ConfidenceIndicator({
  confidence,
  breakdown,
  isCalibrated = false,
  className,
}: ConfidenceIndicatorProps) {
  const percentage = Math.round(confidence * 100);
  const isHigh = confidence >= 0.75;
  const isMedium = confidence >= 0.5 && confidence < 0.75;

  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <div
        className={cn(
          "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border font-mono text-xs font-bold",
          isHigh && "bg-emerald-50 text-emerald-800 border-emerald-200",
          isMedium && "bg-amber-50 text-amber-800 border-amber-200",
          !isHigh && !isMedium && "bg-rose-50 text-rose-800 border-rose-200"
        )}
      >
        {isHigh ? (
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
        ) : (
          <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
        )}
        <span>Confidence: {percentage}%</span>
      </div>

      {!isCalibrated && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex">
                <Badge variant="outline" className="text-[10px] font-mono text-slate-500 cursor-help">
                  Uncalibrated Default
                </Badge>
              </span>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs text-xs">
              This score is an uncalibrated default weight composite across OCR, evidence alignment, and fairness. ASSIST-ONLY mode routes script for examiner confirmation.
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
    </div>
  );
}
