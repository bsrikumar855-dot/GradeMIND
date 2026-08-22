"use client";

import React from "react";
import { cn } from "@/utils/cn";

export interface ShimmerBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
  className?: string;
  variant?: "emerald" | "amber" | "slate" | "blue";
}

export const ShimmerBadge: React.FC<ShimmerBadgeProps> = ({
  children,
  className = "",
  variant = "emerald",
  ...props
}) => {
  const variantStyles = {
    emerald: "bg-emerald-50 text-emerald-800 border-emerald-200/90",
    amber: "bg-amber-50 text-amber-800 border-amber-200/90",
    slate: "bg-slate-100 text-slate-800 border-slate-200",
    blue: "bg-blue-50 text-blue-800 border-blue-200/90",
  };

  return (
    <span
      className={cn(
        "relative inline-flex items-center gap-1.5 overflow-hidden rounded-full border px-2.5 py-0.5 text-xs font-bold transition-all shadow-2xs",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      <span className="relative z-10 flex items-center gap-1.5">{children}</span>
      <span className="absolute inset-0 z-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full animate-[shimmer_2.5s_infinite]" />
    </span>
  );
};
