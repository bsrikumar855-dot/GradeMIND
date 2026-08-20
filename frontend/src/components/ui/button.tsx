import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/utils/cn";
import { LoadingSpinner } from "./loading-spinner";

const buttonVariants = cva(
  "inline-flex items-center justify-center font-medium rounded-md text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 select-none",
  {
    variants: {
      variant: {
        primary: "bg-slate-900 text-white hover:bg-slate-800 active:bg-slate-950 shadow-xs",
        secondary: "bg-slate-100 text-slate-900 hover:bg-slate-200 active:bg-slate-300 border border-slate-200",
        outline: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 active:bg-slate-100 shadow-xs",
        ghost: "bg-transparent text-slate-700 hover:bg-slate-100 active:bg-slate-200",
        danger: "bg-rose-600 text-white hover:bg-rose-700 active:bg-rose-800 shadow-xs",
        accent: "bg-teal-700 text-white hover:bg-teal-800 active:bg-teal-900 shadow-xs",
        academic: "bg-slate-800 text-slate-100 hover:bg-slate-700 active:bg-slate-900 border border-slate-700",
      },
      size: {
        xs: "h-7 px-2.5 text-xs gap-1",
        sm: "h-8 px-3 text-xs gap-1.5",
        md: "h-9 px-4 text-sm gap-2",
        lg: "h-11 px-5 text-base gap-2.5",
        icon: "h-9 w-9 p-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
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
    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || isLoading}
        className={cn(buttonVariants({ variant, size, className }))}
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
