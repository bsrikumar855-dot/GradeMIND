"use client";

import React from "react";
import { cn } from "@/utils/cn";
import { SpotlightCard } from "./spotlight-card";
import { BorderBeam } from "./border-beam";

export interface MagicBentoProps {
  children: React.ReactNode;
  className?: string;
}

export const MagicBentoGrid: React.FC<MagicBentoProps> = ({
  children,
  className = "",
}) => {
  return (
    <div
      className={cn(
        "grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-5 auto-rows-[minmax(180px,auto)] w-full",
        className
      )}
    >
      {children}
    </div>
  );
};

export interface MagicBentoCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  colSpan?: string;
  rowSpan?: "row-span-1" | "row-span-2" | "row-span-3";
  showBeam?: boolean;
  beamColorFrom?: string;
  beamColorTo?: string;
}

export const MagicBentoCard: React.FC<MagicBentoCardProps> = ({
  children,
  className = "",
  colSpan = "col-span-1",
  rowSpan = "row-span-1",
  showBeam = false,
  beamColorFrom = "#74A86D",
  beamColorTo = "#1B432A",
  ...props
}) => {
  return (
    <SpotlightCard
      spotlightColor="rgba(116, 168, 109, 0.12)"
      className={cn(
        "relative rounded-2xl border border-forest-200/80 bg-white p-6 shadow-xs transition-all duration-300 hover:shadow-md hover:border-forest-300 text-left flex flex-col justify-between overflow-hidden",
        colSpan,
        rowSpan,
        className
      )}
      {...props}
    >
      {showBeam && (
        <BorderBeam
          colorFrom={beamColorFrom}
          colorTo={beamColorTo}
          duration={8}
        />
      )}
      {children}
    </SpotlightCard>
  );
};
