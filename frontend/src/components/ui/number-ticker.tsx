"use client";

import React, { useEffect, useState } from "react";
import { cn } from "@/utils/cn";

export interface NumberTickerProps {
  value: number;
  duration?: number;
  decimalPlaces?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
}

export const NumberTicker: React.FC<NumberTickerProps> = ({
  value,
  duration = 1000,
  decimalPlaces = 0,
  suffix = "",
  prefix = "",
  className = "",
}) => {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let startTimestamp: number | null = null;
    const startValue = displayValue;
    const endValue = value;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = startValue + (endValue - startValue) * easeOut;

      setDisplayValue(current);

      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };

    window.requestAnimationFrame(step);
  }, [value, duration]);

  const formatted =
    decimalPlaces > 0
      ? displayValue.toFixed(decimalPlaces)
      : Math.round(displayValue).toString();

  return (
    <span className={cn("inline-block tabular-nums font-extrabold", className)}>
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
};
