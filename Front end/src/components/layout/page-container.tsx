import * as React from "react";
import { cn } from "@/utils/cn";

export interface PageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
}

export const PageContainer: React.FC<PageContainerProps> = ({
  className,
  title,
  description,
  actions,
  children,
  ...props
}) => {
  return (
    <div
      className={cn(
        "flex flex-col gap-6 p-6 md:p-8 max-w-7xl mx-auto w-full",
        className
      )}
      {...props}
    >
      {(title || description || actions) && (
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-100 dark:border-gray-900 pb-5">
          <div className="space-y-1">
            {title && (
              <h1 className="text-2xl font-bold tracking-tight text-gray-950 dark:text-gray-50">
                {title}
              </h1>
            )}
            {description && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {description}
              </p>
            )}
          </div>
          {actions && <div className="flex items-center gap-3 shrink-0">{actions}</div>}
        </div>
      )}
      <div className="flex-1">{children}</div>
    </div>
  );
};

PageContainer.displayName = "PageContainer";
