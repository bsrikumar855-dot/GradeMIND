import * as React from "react";
import { FileText, ZoomIn, ZoomOut, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/cn";

export interface AnswerSheetViewerProps {
  imageUrl?: string;
  extractedText?: string;
  studentName?: string;
  studentRollNumber?: string;
  className?: string;
}

export function AnswerSheetViewer({
  imageUrl,
  extractedText = "",
  studentName,
  studentRollNumber,
  className,
}: AnswerSheetViewerProps) {
  const [zoom, setZoom] = React.useState(100);

  return (
    <div className={cn("calm-card grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-200 min-h-[450px]", className)}>
      {/* Left: Scanned Document Page */}
      <div className="p-4 flex flex-col justify-between space-y-3 bg-slate-50/50">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <span className="text-metadata text-xs font-bold text-slate-700">Original Answer Sheet Scan</span>
          <div className="flex items-center gap-1">
            <Button size="xs" variant="outline" onClick={() => setZoom((z) => Math.max(50, z - 25))}>
              <ZoomOut className="h-3 w-3" />
            </Button>
            <span className="font-mono text-[11px] px-1 text-slate-600">{zoom}%</span>
            <Button size="xs" variant="outline" onClick={() => setZoom((z) => Math.min(200, z + 25))}>
              <ZoomIn className="h-3 w-3" />
            </Button>
          </div>
        </div>

        <div className="flex-1 flex items-center justify-center overflow-auto p-2 bg-slate-100/80 rounded border border-slate-200 min-h-[300px]">
          {imageUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={imageUrl}
              alt="Student Answer Sheet Scan"
              style={{ transform: `scale(${zoom / 100})`, transformOrigin: "top center" }}
              className="max-w-full max-h-full object-contain shadow-xs transition-transform duration-200"
            />
          ) : (
            <div className="text-center p-6 space-y-2 text-slate-400">
              <FileText className="h-10 w-10 mx-auto stroke-1" />
              <p className="text-xs font-medium">Scanned page image viewer</p>
              <p className="text-[11px] font-mono">Roll: {studentRollNumber || "N/A"}</p>
            </div>
          )}
        </div>
      </div>

      {/* Right: Extracted OCR / HTR Text */}
      <div className="p-4 flex flex-col justify-between space-y-3 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <span className="text-metadata text-xs font-bold text-slate-700">Extracted HTR Text Line Stream</span>
          <span className="text-xs font-mono text-slate-400">{extractedText.length} Chars</span>
        </div>

        <div className="flex-1 overflow-auto p-4 bg-slate-50 rounded border border-slate-200/80 font-mono text-xs text-slate-800 leading-relaxed whitespace-pre-wrap min-h-[300px]">
          {extractedText || "No OCR extracted text line stream available for this script."}
        </div>
      </div>
    </div>
  );
}
