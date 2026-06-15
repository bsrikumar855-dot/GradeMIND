"use client";

import * as React from "react";
import Image from "next/image";

export type LogoVariant =
  | "full-color"
  | "mono-dark"
  | "mono-light"
  | "navbar"
  | "sidebar"
  | "favicon";

export interface GradeMindLogoProps {
  variant?: LogoVariant;
  className?: string;
  showText?: boolean;
  size?: number;
  textSize?: "sm" | "md" | "lg" | "xl";
}

export const GRADEMIND_LOGO_SRC = "/images/grademind-logo-official.jpeg";

const DEFAULT_SIZES: Record<LogoVariant, number> = {
  "full-color": 44,
  "mono-dark": 44,
  "mono-light": 44,
  navbar: 32,
  sidebar: 32,
  favicon: 32,
};

const TEXT_CLASSES: Record<NonNullable<GradeMindLogoProps["textSize"]>, string> = {
  sm: "text-base",
  md: "text-xl",
  lg: "text-2xl",
  xl: "text-3xl",
};

export const GradeMindLogo: React.FC<GradeMindLogoProps> = ({
  variant = "full-color",
  className,
  showText = true,
  size,
  textSize = "md",
}) => {
  const iconSize = size ?? DEFAULT_SIZES[variant];

  return (
    <div className={`inline-flex items-center gap-2.5 ${className ?? ""}`}>
      <Image
        src={GRADEMIND_LOGO_SRC}
        alt="GradeMIND logo"
        width={iconSize}
        height={iconSize}
        className="shrink-0 object-contain"
        priority={variant === "navbar" || variant === "sidebar"}
      />
      {showText && (
        <span className={`font-extrabold tracking-tight text-brand-dark ${TEXT_CLASSES[textSize]}`}>
          GradeMIND
        </span>
      )}
    </div>
  );
};

GradeMindLogo.displayName = "GradeMindLogo";

export default GradeMindLogo;
