import * as React from "react";
import { Eye, FileCheck, Layers, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

export interface OCRStatusProps {
  confidence: number;
  lineCount: number;
  provider?: string;
  isFallback?: boolean;
  className?: string;
}

export function OCRStatus({
  confidence,
  lineCount,
  provider = "TrOCR / EasyOCR Router",
  isFallback = false,
  className,
}: OCRStatusProps) {
  const percentage = Math.round(confidence * 100);

  return (
    <div className={cn("calm-card p-4 space-y-2.5", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Eye className="h-4 w-4 text-slate-700" />
          <h4 className="text-heading text-xs font-bold uppercase tracking-wider text-slate-800">
            OCR / HTR Extraction Status
          </h4>
        </div>
        <Badge variant={isFallback ? "warning" : "success"} className="text-[10px] font-mono">
          {percentage}% Text Confidence
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
        <div className="p-2 rounded bg-slate-50 border border-slate-100">
          <span className="text-metadata text-[10px] text-slate-400 block">Lines Extracted</span>
          <span className="font-bold text-slate-900">{lineCount} Lines</span>
        </div>
        <div className="p-2 rounded bg-slate-50 border border-slate-100">
          <span className="text-metadata text-[10px] text-slate-400 block">Active Engine</span>
          <span className="font-bold text-slate-900 truncate block">{provider}</span>
        </div>
      </div>

      {isFallback && (
        <p className="text-[11px] text-amber-800 bg-amber-50 p-2 rounded border border-amber-200">
          Local OCR confidence was below 70%. Triggered secondary Gemini Vision OCR fallback.
        </p>
      )}
    </div>
  );
}
