import * as React from "react";
import { cn } from "@/utils/cn";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "success" | "warning" | "danger" | "info" | "neutral";
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = "neutral",
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold select-none border";

  const variants = {
    success:
      "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/35 dark:bg-emerald-950/30 dark:text-emerald-400",
    warning:
      "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/35 dark:bg-amber-950/30 dark:text-amber-400",
    danger:
      "border-red-200 bg-red-50 text-red-700 dark:border-red-900/35 dark:bg-red-950/30 dark:text-red-400",
    info:
      "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/35 dark:bg-blue-950/30 dark:text-blue-400",
    neutral:
      "border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400",
  };

  return (
    <span
      className={cn(baseStyles, variants[variant], className)}
      {...props}
    />
  );
};

Badge.displayName = "Badge";
