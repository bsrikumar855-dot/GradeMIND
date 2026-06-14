import * as React from "react";
import { Filter } from "lucide-react";
import { cn } from "@/utils/cn";

export interface FilterOption {
  label: string;
  value: string;
}

export interface FilterDropdownProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: FilterOption[];
  wrapperClassName?: string;
}

export const FilterDropdown = React.forwardRef<HTMLSelectElement, FilterDropdownProps>(
  ({ className, label, options, wrapperClassName, id, ...props }, ref) => {
    const generatedId = React.useId();
    const selectId = id || generatedId;

    return (
      <div className={cn("relative flex items-center min-w-[140px]", wrapperClassName)}>
        <div className="absolute left-3.5 pointer-events-none text-gray-400 dark:text-gray-500">
          <Filter className="h-4 w-4" />
        </div>
        <select
          ref={ref}
          id={selectId}
          className={cn(
            "w-full rounded-lg border border-gray-300 bg-white pl-10 pr-8 py-2.5 text-xs font-semibold text-gray-650 cursor-pointer outline-none transition-shadow hover:bg-gray-50 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:opacity-50 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-350 dark:hover:bg-gray-850 dark:focus:border-blue-500 dark:focus:ring-blue-950/30 appearance-none",
            className
          )}
          {...props}
        >
          {label && <option value="">{label}</option>}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {/* Custom Chevron Indicator */}
        <div className="absolute right-3.5 pointer-events-none flex items-center justify-center text-gray-400 dark:text-gray-500">
          <svg
            className="h-4 w-4 fill-current"
            viewBox="0 0 20 20"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </div>
      </div>
    );
  }
);

FilterDropdown.displayName = "FilterDropdown";
