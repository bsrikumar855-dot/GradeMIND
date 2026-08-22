"use client";

import React from "react";
import { cn } from "@/utils/cn";

export interface BorderBeamProps {
  className?: string;
  size?: number;
  duration?: number;
  delay?: number;
  colorFrom?: string;
  colorTo?: string;
}

export const BorderBeam: React.FC<BorderBeamProps> = ({
  className,
  size = 200,
  duration = 8,
  delay = 0,
  colorFrom = "#10b981",
  colorTo = "#06b6d4",
}) => {
  return (
    <div
      style={
        {
          "--size": `${size}px`,
          "--duration": `${duration}s`,
          "--delay": `${delay}s`,
          "--color-from": colorFrom,
          "--color-to": colorTo,
        } as React.CSSProperties
      }
      className={cn(
        "pointer-events-none absolute inset-0 rounded-[inherit] border border-transparent [mask-clip:padding-box,border-box] [mask-composite:intersect] [mask-image:linear-gradient(transparent,transparent),linear-gradient(#000,#000)]",
        "after:absolute after:aspect-square after:w-[var(--size)] after:animate-border-beam after:bg-[linear-gradient(to_left,var(--color-from),var(--color-to),transparent)] after:[offset-anchor:100%_50%] after:[offset-path:rect(0_auto_auto_0_round_inherit)]",
        className
      )}
    />
  );
};
