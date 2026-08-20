import * as React from "react";
import { cn } from "@/utils/cn";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helperText, id, rows = 4, ...props }, ref) => {
    const generatedId = React.useId();
    const textareaId = id || generatedId;

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={textareaId} className="text-metadata text-slate-700 block">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          rows={rows}
          className={cn(
            "flex w-full rounded-md border border-slate-200 bg-white p-3 text-sm text-slate-900 placeholder:text-slate-400 transition-colors focus-visible:outline-none focus-visible:border-slate-400 focus-visible:ring-1 focus-visible:ring-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:opacity-50 resize-y leading-relaxed",
            error && "border-rose-500 focus-visible:border-rose-500 focus-visible:ring-rose-500",
            className
          )}
          {...props}
        />
        {error ? (
          <p className="text-xs font-medium text-rose-600">{error}</p>
        ) : helperText ? (
          <p className="text-xs text-slate-500">{helperText}</p>
        ) : null}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
