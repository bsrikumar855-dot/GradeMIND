import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/utils/cn";

export interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  progress?: {
    value: number; // 0 to 100
    colorClass?: string;
  };
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  description,
  progress,
  className,
}) => {
  return (
    <Card className={cn(className)}>
      <CardContent className="p-6">
        <span className="text-xs font-bold text-gray-400 dark:text-gray-505 uppercase tracking-wider">
          {title}
        </span>
        <div className="mt-2 text-2xl font-bold text-gray-950 dark:text-gray-55">
          {value}
        </div>
        {description && (
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {description}
          </p>
        )}
        {progress && (
          <div className="mt-4 space-y-1.5">
            <div className="h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-800">
              <div
                className={cn("h-full rounded-full bg-blue-600", progress.colorClass)}
                style={{ width: `${Math.min(100, Math.max(0, progress.value))}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] font-semibold text-gray-550 dark:text-gray-400">
              <span>Progress</span>
              <span>{progress.value}%</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

StatCard.displayName = "StatCard";
