import * as React from "react";
import { Brain, Layers, BarChart3 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

export interface CognitiveTier {
  category: "REMEMBER" | "UNDERSTAND" | "APPLY" | "ANALYZE" | "EVALUATE" | "CREATE";
  score: number;
  maxScore: number;
}

export interface LearningInsightProps {
  bloomTiers?: CognitiveTier[];
  masteryPercentage?: number;
  className?: string;
}

const defaultTiers: CognitiveTier[] = [
  { category: "REMEMBER", score: 8, maxScore: 10 },
  { category: "UNDERSTAND", score: 7, maxScore: 10 },
  { category: "APPLY", score: 6, maxScore: 10 },
  { category: "ANALYZE", score: 5, maxScore: 10 },
];

export function LearningInsight({
  bloomTiers = defaultTiers,
  masteryPercentage = 72,
  className,
}: LearningInsightProps) {
  return (
    <div className={cn("calm-card p-5 space-y-4", className)}>
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-slate-800" />
          <h3 className="text-heading text-sm font-bold">Cognitive & Learning Analytics</h3>
        </div>
        <Badge variant="academic" className="font-mono">
          Mastery: {masteryPercentage}%
        </Badge>
      </div>

      <div className="space-y-2">
        <span className="text-metadata text-[10px] text-slate-500 block">
          Bloom&apos;s Taxonomy Cognitive Tier Performance
        </span>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {bloomTiers.map((tier) => {
            const pct = Math.round((tier.score / (tier.maxScore || 1)) * 100);
            return (
              <div key={tier.category} className="p-2.5 rounded bg-slate-50 border border-slate-200/80 text-xs space-y-1">
                <span className="text-metadata text-[10px] text-slate-400 block">{tier.category}</span>
                <div className="flex items-baseline justify-between">
                  <span className="font-bold text-slate-900 font-mono text-sm">{tier.score}/{tier.maxScore}</span>
                  <span className="text-[11px] font-mono font-medium text-slate-600">{pct}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
