import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/utils/cn";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-slate-200 bg-slate-100 text-slate-800",
        primary: "border-blue-200 bg-blue-50 text-blue-800",
        secondary: "border-slate-300 bg-slate-200 text-slate-900",
        success: "border-emerald-200 bg-emerald-50 text-emerald-800",
        warning: "border-amber-200 bg-amber-50 text-amber-900",
        danger: "border-rose-200 bg-rose-50 text-rose-800",
        info: "border-sky-200 bg-sky-50 text-sky-800",
        academic: "border-slate-300 bg-slate-100 text-slate-900 font-mono text-[11px]",
        outline: "border-slate-300 bg-transparent text-slate-700",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  icon?: React.ReactNode;
}

export function Badge({ className, variant, icon, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props}>
      {icon && <span className="mr-1 flex items-center">{icon}</span>}
      {children}
    </div>
  );
}
