import * as React from "react";
import { FolderOpen } from "lucide-react";
import { cn } from "@/utils/cn";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  className,
  icon,
  title,
  description,
  action,
  ...props
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-300 p-8 text-center dark:border-gray-800",
        className
      )}
      {...props}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gray-50 text-gray-500 dark:bg-gray-900 dark:text-gray-400">
        {icon || <FolderOpen className="h-6 w-6" />}
      </div>
      <h3 className="mt-4 text-base font-semibold text-gray-950 dark:text-gray-50">
        {title}
      </h3>
      <p className="mt-2 text-sm text-gray-500 max-w-sm dark:text-gray-400">
        {description}
      </p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
};

EmptyState.displayName = "EmptyState";
