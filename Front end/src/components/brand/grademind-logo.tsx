"use client";

import * as React from "react";

// ===================================================================
// GradeMIND Logo Component — Brand Identity System
// ===================================================================
// Faithfully reproduces the GradeMIND brain+checkmark icon
// using the official GradeMIND Design System color palette.
//
// Logo concept: A brain hemisphere (left) with neural network
// pathways inside, overlaid by a bold checkmark — representing
// "AI-powered grading" (brain = AI/Mind, checkmark = grading).
// ===================================================================

// ── Color palette ──────────────────────────────────────────────────
const BRAND = {
  darkGreen:    "#2F5A3A",
  primaryGreen: "#86B77B",
  lightSage:    "#CFE8C2",
  background:   "#FFFDF8",
  accent:       "#5B8DEF",
  white:        "#FFFFFF",
} as const;

// ── Types ──────────────────────────────────────────────────────────
export type LogoVariant =
  | "full-color"
  | "mono-dark"
  | "mono-light"
  | "navbar"
  | "sidebar"
  | "favicon";

export interface GradeMindLogoProps {
  /** Visual variant of the logo */
  variant?: LogoVariant;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show the "GradeMIND" wordmark next to the icon */
  showText?: boolean;
  /** Icon size in pixels (auto-set per variant if omitted) */
  size?: number;
  /** Wordmark text size preset */
  textSize?: "sm" | "md" | "lg" | "xl";
}

// ── Color resolver ─────────────────────────────────────────────────
function resolveColors(variant: LogoVariant) {
  switch (variant) {
    case "full-color":
      return {
        brain:     BRAND.darkGreen,
        checkmark: BRAND.primaryGreen,
        text:      BRAND.darkGreen,
        bg:        "transparent",
      };
    case "mono-dark":
      return {
        brain:     BRAND.darkGreen,
        checkmark: BRAND.darkGreen,
        text:      BRAND.darkGreen,
        bg:        "transparent",
      };
    case "mono-light":
      return {
        brain:     BRAND.white,
        checkmark: BRAND.white,
        text:      BRAND.white,
        bg:        "transparent",
      };
    case "navbar":
      return {
        brain:     BRAND.darkGreen,
        checkmark: BRAND.primaryGreen,
        text:      BRAND.darkGreen,
        bg:        "transparent",
      };
    case "sidebar":
      return {
        brain:     BRAND.darkGreen,
        checkmark: BRAND.primaryGreen,
        text:      BRAND.darkGreen,
        bg:        "transparent",
      };
    case "favicon":
      return {
        brain:     BRAND.white,
        checkmark: BRAND.primaryGreen,
        text:      BRAND.white,
        bg:        BRAND.darkGreen,
      };
  }
}

// ── Brain + Checkmark Icon SVG ─────────────────────────────────────
// This is the core icon mark: left brain hemisphere with neural
// network pathways, and a bold checkmark sweeping through it.
interface BrainCheckIconProps {
  brainColor: string;
  checkColor: string;
  size?: number;
  className?: string;
}

const BrainCheckIcon: React.FC<BrainCheckIconProps> = ({
  brainColor,
  checkColor,
  size = 32,
  className,
}) => {
  // Maintain aspect ratio (viewBox is 52 wide × 56 tall)
  const h = size * (56 / 52);
  return (
    <svg
      width={size}
      height={h}
      viewBox="0 0 52 56"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* ── Brain hemisphere arc (left side) ──────────────── */}
      <path
        d="M 27 4 C 14 4 4 15 4 28 C 4 41 14 52 27 52"
        stroke={brainColor}
        strokeWidth="3.5"
        strokeLinecap="round"
        fill="none"
      />

      {/* ── Neural network pathways (from center hub) ────── */}
      {/* Upper-left pathway */}
      <path
        d="M 27 28 C 24 23 19 16 15 10"
        stroke={brainColor}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* Left pathway */}
      <path
        d="M 27 28 C 21 27 15 25 8 23"
        stroke={brainColor}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* Lower-left pathway */}
      <path
        d="M 27 28 C 24 33 19 40 15 46"
        stroke={brainColor}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* Top-center pathway */}
      <path
        d="M 27 28 C 26 22 23 14 20 7"
        stroke={brainColor}
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {/* Bottom-center pathway */}
      <path
        d="M 27 28 C 26 34 23 42 20 49"
        stroke={brainColor}
        strokeWidth="2.5"
        strokeLinecap="round"
      />

      {/* ── Central hub node ──────────────────────────────── */}
      <circle cx="27" cy="28" r="2.8" fill={brainColor} />

      {/* ── Peripheral nodes (at pathway endpoints) ──────── */}
      <circle cx="15" cy="10" r="2" fill={brainColor} />
      <circle cx="8"  cy="23" r="2" fill={brainColor} />
      <circle cx="15" cy="46" r="2" fill={brainColor} />
      <circle cx="20" cy="7"  r="1.6" fill={brainColor} />
      <circle cx="20" cy="49" r="1.6" fill={brainColor} />

      {/* ── Right-side organic elements (leaf/growth) ────── */}
      {/* Upper leaf */}
      <path
        d="M 31 20 C 36 15 42 14 44 18 C 40 20 36 25 32 28"
        stroke={brainColor}
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />
      {/* Lower leaf */}
      <path
        d="M 31 36 C 36 41 42 42 44 38 C 40 36 36 31 32 28"
        stroke={brainColor}
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />

      {/* ── Checkmark (grading verification) ─────────────── */}
      <path
        d="M 11 40 L 24 53 L 48 7"
        stroke={checkColor}
        strokeWidth="4.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
};

BrainCheckIcon.displayName = "BrainCheckIcon";

// ── Simplified icon for very small sizes (favicon) ─────────────────
const BrainCheckIconSimplified: React.FC<BrainCheckIconProps> = ({
  brainColor,
  checkColor,
  size = 24,
  className,
}) => {
  const h = size * (56 / 52);
  return (
    <svg
      width={size}
      height={h}
      viewBox="0 0 52 56"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Brain arc (simplified) */}
      <path
        d="M 27 4 C 14 4 4 15 4 28 C 4 41 14 52 27 52"
        stroke={brainColor}
        strokeWidth="4"
        strokeLinecap="round"
        fill="none"
      />

      {/* 3 main neural pathways */}
      <path d="M 27 28 C 24 23 19 16 15 10" stroke={brainColor} strokeWidth="3" strokeLinecap="round" />
      <path d="M 27 28 C 21 27 15 25 8 23" stroke={brainColor} strokeWidth="3" strokeLinecap="round" />
      <path d="M 27 28 C 24 33 19 40 15 46" stroke={brainColor} strokeWidth="3" strokeLinecap="round" />

      {/* Center node */}
      <circle cx="27" cy="28" r="3.5" fill={brainColor} />

      {/* Bold checkmark */}
      <path
        d="M 11 40 L 24 53 L 48 7"
        stroke={checkColor}
        strokeWidth="5.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
};

BrainCheckIconSimplified.displayName = "BrainCheckIconSimplified";

// ── Text size presets ──────────────────────────────────────────────
const TEXT_SIZES = {
  sm: { fontSize: "1rem",    letterSpacing: "-0.01em" },
  md: { fontSize: "1.25rem", letterSpacing: "-0.015em" },
  lg: { fontSize: "1.5rem",  letterSpacing: "-0.02em" },
  xl: { fontSize: "2rem",    letterSpacing: "-0.025em" },
} as const;

// ── Main Logo Component ────────────────────────────────────────────
export const GradeMindLogo: React.FC<GradeMindLogoProps> = ({
  variant = "full-color",
  className,
  showText = true,
  size,
  textSize = "md",
}) => {
  const colors = resolveColors(variant);

  // Default icon sizes per variant
  const defaultSizes: Record<LogoVariant, number> = {
    "full-color": 40,
    "mono-dark":  40,
    "mono-light": 40,
    navbar:       26,
    sidebar:      30,
    favicon:      28,
  };

  const iconSize = size ?? defaultSizes[variant];
  const ts = TEXT_SIZES[textSize];

  // ── Favicon variant (icon in dark-green rounded square) ──────
  if (variant === "favicon") {
    const pad = Math.round(iconSize * 0.25);
    const boxSize = iconSize + pad * 2;
    return (
      <div
        className={`inline-flex items-center justify-center ${className ?? ""}`}
        style={{
          width: boxSize,
          height: boxSize,
          borderRadius: boxSize * 0.22,
          background: `linear-gradient(135deg, ${BRAND.darkGreen} 0%, #1d3d24 100%)`,
        }}
      >
        <BrainCheckIconSimplified
          brainColor={colors.brain}
          checkColor={colors.checkmark}
          size={iconSize}
        />
      </div>
    );
  }

  // ── All other variants ───────────────────────────────────────
  return (
    <div className={`inline-flex items-center gap-2.5 ${className ?? ""}`}>
      <BrainCheckIcon
        brainColor={colors.brain}
        checkColor={colors.checkmark}
        size={iconSize}
      />
      {showText && (
        <span
          style={{
            color: colors.text,
            fontFamily: "var(--font-playfair), 'Playfair Display', Georgia, serif",
            fontSize: ts.fontSize,
            letterSpacing: ts.letterSpacing,
            fontWeight: 700,
            lineHeight: 1,
          }}
        >
          Grade
          <span style={{ fontWeight: 900 }}>MIND</span>
        </span>
      )}
    </div>
  );
};

GradeMindLogo.displayName = "GradeMindLogo";

// ── Standalone exports for direct SVG usage ────────────────────────
export { BrainCheckIcon, BrainCheckIconSimplified };
export default GradeMindLogo;
