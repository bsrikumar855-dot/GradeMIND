import * as React from "react";
import { UserCheck, AlertTriangle, ArrowRight, CheckCircle2 } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { StatusIndicator } from "@/components/ui/status-indicator";
import { cn } from "@/utils/cn";

export interface ReviewQueueItem {
  id: string;
  studentName: string;
  studentRollNumber: string;
  examTitle: string;
  obtainedMarks?: number;
  totalMarks?: number;
  status: string;
  updatedAt?: string;
  reason?: string;
}

export interface ReviewQueueProps {
  items: ReviewQueueItem[];
  onReviewItem?: (id: string) => void;
  className?: string;
}

export function ReviewQueue({ items = [], onReviewItem, className }: ReviewQueueProps) {
  if (items.length === 0) {
    return (
      <div className="calm-card p-8 text-center space-y-2">
        <CheckCircle2 className="h-8 w-8 text-emerald-600 mx-auto" />
        <h4 className="text-heading text-sm">No Pending Examiner Reviews</h4>
        <p className="text-caption text-xs text-slate-500 max-w-sm mx-auto">
          All submissions have passed deterministic verification thresholds or been confirmed by examiners.
        </p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <UserCheck className="h-4 w-4 text-amber-600" />
          <h3 className="text-heading text-sm font-bold">Examiner Review Queue</h3>
        </div>
        <span className="text-metadata text-xs font-mono text-amber-700">
          {items.length} Requires Manual Confirmation
        </span>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Student</TableHead>
            <TableHead>Roll Number</TableHead>
            <TableHead>Assessment</TableHead>
            <TableHead>Proposed Score</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id}>
              <TableCell className="font-semibold text-slate-900">{item.studentName}</TableCell>
              <TableCell className="font-mono text-xs text-slate-600">
                {item.studentRollNumber}
              </TableCell>
              <TableCell className="text-xs text-slate-700">{item.examTitle}</TableCell>
              <TableCell className="font-mono font-bold text-slate-900">
                {item.obtainedMarks !== undefined ? `${item.obtainedMarks}/${item.totalMarks}` : "N/A"}
              </TableCell>
              <TableCell>
                <StatusIndicator status={item.status} />
              </TableCell>
              <TableCell className="text-right">
                {onReviewItem && (
                  <Button
                    size="xs"
                    variant="outline"
                    onClick={() => onReviewItem(item.id)}
                    rightIcon={<ArrowRight className="h-3 w-3" />}
                  >
                    Review Marks
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
