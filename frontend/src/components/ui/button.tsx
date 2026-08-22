import * as React from "react";
import { cn } from "@/utils/cn";
import { LoadingSpinner } from "./loading-spinner";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      type = "button",
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-bold rounded-xl transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-xs active:translate-y-0 active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer";

    const variants = {
      primary:
        "bg-[#183B25] text-white hover:bg-[#112B1B] active:bg-[#0F2618] focus-visible:ring-[#4A8B40] border border-emerald-800/40",
      secondary:
        "bg-emerald-100 text-black hover:bg-emerald-200 active:bg-emerald-300 focus-visible:ring-emerald-400 border border-emerald-300",
      outline:
        "border-2 border-emerald-800/30 bg-transparent text-black hover:bg-emerald-50 active:bg-emerald-100 focus-visible:ring-emerald-400",
      ghost:
        "bg-transparent text-black hover:bg-emerald-100/70 active:bg-emerald-200",
      danger:
        "bg-rose-700 text-white hover:bg-rose-800 active:bg-rose-900 focus-visible:ring-rose-500",
    };

    const sizes = {
      sm: "h-8 px-3.5 text-xs gap-1.5",
      md: "h-10 px-4 text-xs gap-2",
      lg: "h-12 px-6 text-sm gap-2.5",
    };

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && <LoadingSpinner size="sm" className="text-current" />}
        {!isLoading && leftIcon && <span className="flex items-center">{leftIcon}</span>}
        {children}
        {!isLoading && rightIcon && <span className="flex items-center">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = "Button";
