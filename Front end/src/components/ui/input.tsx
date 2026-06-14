import * as React from "react";
import { cn } from "@/utils/cn";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", label, error, helperText, id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-xs font-semibold text-gray-700 uppercase tracking-wider dark:text-gray-300"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            type={type}
            id={inputId}
            className={cn(
              "flex w-full rounded-lg border border-gray-300 bg-white px-3.5 py-2.5 text-sm text-gray-950 placeholder-gray-400 outline-none transition-shadow focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:placeholder-gray-500 dark:focus:border-blue-500 dark:focus:ring-blue-950/30",
              error && "border-red-500 focus:border-red-500 focus:ring-red-100 dark:border-red-500 dark:focus:border-red-500 dark:focus:ring-red-950/30",
              className
            )}
            {...props}
          />
        </div>
        {error ? (
          <p className="text-xs font-medium text-red-600 dark:text-red-400">
            {error}
          </p>
        ) : helperText ? (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {helperText}
          </p>
        ) : null}
      </div>
    );
  }
);

Input.displayName = "Input";
