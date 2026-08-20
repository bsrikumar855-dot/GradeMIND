import * as React from "react";
import { CheckCircle2, Circle, Clock } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/utils/cn";

export interface ProgressStage {
  id: string;
  name: string;
  status: "COMPLETED" | "PROCESSING" | "PENDING" | "FAILED";
}

export interface AssessmentProgressProps {
  stages?: ProgressStage[];
  currentStageId?: string;
  className?: string;
}

const defaultStages: ProgressStage[] = [
  { id: "upload", name: "Answer Sheet Upload", status: "COMPLETED" },
  { id: "ocr", name: "HTR Text Extraction", status: "COMPLETED" },
  { id: "segmentation", name: "Question Segmentation", status: "COMPLETED" },
  { id: "evaluation", name: "Value-Point Rubric Scoring", status: "PROCESSING" },
  { id: "verification", name: "Gemini Verification Check", status: "PENDING" },
  { id: "report", name: "Report & Insights Assembly", status: "PENDING" },
];

export function AssessmentProgress({
  stages = defaultStages,
  currentStageId,
  className,
}: AssessmentProgressProps) {
  const completedCount = stages.filter((s) => s.status === "COMPLETED").length;
  const progressPercent = Math.round((completedCount / stages.length) * 100);

  return (
    <div className={cn("calm-card p-5 space-y-4", className)}>
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-heading text-sm font-bold">Evaluation Pipeline Telemetry</h4>
          <p className="text-caption text-xs text-slate-500">
            {completedCount} of {stages.length} pipeline verification gates passed
          </p>
        </div>
        <span className="font-mono text-sm font-bold text-slate-900">{progressPercent}%</span>
      </div>

      <Progress value={progressPercent} indicatorClassName="bg-teal-600" />

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 pt-2">
        {stages.map((stage, idx) => {
          const isDone = stage.status === "COMPLETED";
          const isCurrent = stage.status === "PROCESSING" || stage.id === currentStageId;
          const isFailed = stage.status === "FAILED";

          return (
            <div
              key={stage.id}
              className={cn(
                "p-2.5 rounded-md border text-xs space-y-1 transition-colors",
                isDone && "bg-emerald-50/50 border-emerald-200 text-emerald-950",
                isCurrent && "bg-blue-50/60 border-blue-300 text-blue-950 ring-1 ring-blue-300",
                isFailed && "bg-rose-50 border-rose-200 text-rose-950",
                !isDone && !isCurrent && !isFailed && "bg-slate-50 border-slate-200 text-slate-500"
              )}
            >
              <div className="flex items-center justify-between">
                <span className="text-metadata text-[10px] opacity-75">Stage {idx + 1}</span>
                {isDone ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                ) : isCurrent ? (
                  <Clock className="h-3.5 w-3.5 text-blue-600 animate-spin" />
                ) : (
                  <Circle className="h-3.5 w-3.5 text-slate-400" />
                )}
              </div>
              <p className="font-semibold leading-snug line-clamp-2">{stage.name}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
