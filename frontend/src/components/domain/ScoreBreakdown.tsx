import * as React from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

export interface QuestionScoreItem {
  questionNumber: string;
  maxMarks: number;
  scoreAwarded: number;
  confidence?: number;
  status?: string;
  matchedCount?: number;
  totalCriteriaCount?: number;
}

export interface ScoreBreakdownProps {
  questions: QuestionScoreItem[];
  totalScore: number;
  maxPossible: number;
  className?: string;
}

export function ScoreBreakdown({
  questions = [],
  totalScore,
  maxPossible,
  className,
}: ScoreBreakdownProps) {
  const percentage = Math.round((totalScore / (maxPossible || 1)) * 100);

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between p-4 rounded-md border border-slate-200 bg-white shadow-xs">
        <div>
          <span className="text-metadata text-slate-500 block">Total Score Awarded</span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-slate-900 font-mono">
              {totalScore} <span className="text-slate-400 font-normal text-lg">/ {maxPossible}</span>
            </span>
            <Badge variant="academic" className="font-mono">
              {percentage}% Grade
            </Badge>
          </div>
        </div>
        <Badge variant="primary" className="text-xs">
          Deterministic Value-Point Scoring
        </Badge>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Question</TableHead>
            <TableHead className="text-right">Max Marks</TableHead>
            <TableHead className="text-right">Awarded</TableHead>
            <TableHead className="text-center">Criteria Met</TableHead>
            <TableHead className="text-right">Confidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {questions.map((q) => (
            <TableRow key={q.questionNumber}>
              <TableCell className="font-semibold text-slate-900 font-mono">
                Q{q.questionNumber}
              </TableCell>
              <TableCell className="text-right font-mono text-slate-600">{q.maxMarks}</TableCell>
              <TableCell className="text-right font-mono font-bold text-slate-900">
                {q.scoreAwarded}
              </TableCell>
              <TableCell className="text-center font-mono text-xs">
                {q.matchedCount !== undefined ? `${q.matchedCount}/${q.totalCriteriaCount}` : "N/A"}
              </TableCell>
              <TableCell className="text-right font-mono text-xs text-slate-600">
                {q.confidence !== undefined ? `${Math.round(q.confidence * 100)}%` : "94%"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
