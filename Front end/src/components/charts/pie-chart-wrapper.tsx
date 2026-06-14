import * as React from "react";
import { cn } from "@/utils/cn";

export interface PieChartData {
  label: string;
  value: number;
  color: string;
}

export interface PieChartWrapperProps {
  data: PieChartData[];
  height?: number;
  className?: string;
}

export const PieChartWrapper: React.FC<PieChartWrapperProps> = ({
  data,
  height = 200,
  className,
}) => {
  const total = React.useMemo(() => data.reduce((acc, curr) => acc + curr.value, 0), [data]);

  // Generate SVG paths for Pie Slices
  const slices = React.useMemo(() => {
    let accumulatedAngle = 0;
    return data.map((item) => {
      const percentage = total > 0 ? (item.value / total) * 100 : 0;
      const angle = (percentage / 100) * 360;

      // Coordinate calculations for arc
      const x1 = Math.cos((accumulatedAngle - 90) * (Math.PI / 180));
      const y1 = Math.sin((accumulatedAngle - 90) * (Math.PI / 180));

      accumulatedAngle += angle;

      const x2 = Math.cos((accumulatedAngle - 90) * (Math.PI / 180));
      const y2 = Math.sin((accumulatedAngle - 90) * (Math.PI / 180));

      // SVG path parameters
      const radius = 0.8; // Scale factor
      const sx = x1 * radius + 1;
      const sy = y1 * radius + 1;
      const ex = x2 * radius + 1;
      const ey = y2 * radius + 1;

      const largeArcFlag = angle > 180 ? 1 : 0;

      // If single slice takes up whole circle
      const pathData =
        percentage >= 99.99
          ? "M 1 0.2 A 0.8 0.8 0 1 1 0.999 0.2 Z"
          : `M 1 1 L ${sx} ${sy} A 0.8 0.8 0 ${largeArcFlag} 1 ${ex} ${ey} Z`;

      return {
        ...item,
        pathData,
        percentage: percentage.toFixed(1),
      };
    });
  }, [data, total]);

  return (
    <div className={cn("flex flex-col items-center sm:flex-row gap-6", className)} style={{ minHeight: height }}>
      {/* SVG Canvas */}
      <div className="relative shrink-0 flex items-center justify-center" style={{ width: height, height: height }}>
        <svg viewBox="0 0 2 2" className="w-full h-full transform -rotate-90">
          {slices.map((slice, i) => (
            <path
              key={i}
              d={slice.pathData}
              fill={slice.color}
              className="transition-all duration-300 hover:opacity-90 hover:scale-102 origin-center cursor-pointer"
            />
          ))}
          {/* Inner circle for Donut effect */}
          <circle cx="1" cy="1" r="0.45" fill="white" className="dark:fill-gray-950" />
        </svg>

        {/* Center Text displaying total */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-[10px] uppercase font-bold tracking-wider text-gray-400">Total</span>
          <span className="text-xl font-extrabold text-gray-950 dark:text-gray-50">{total}</span>
        </div>
      </div>

      {/* Legend Block */}
      <div className="flex-1 space-y-2.5 w-full">
        {slices.map((slice, idx) => (
          <div key={idx} className="flex items-center justify-between text-xs hover:bg-gray-50 dark:hover:bg-gray-900 p-1.5 rounded-lg transition-colors">
            <div className="flex items-center gap-2.5">
              <span className="h-3 w-3 rounded-full shrink-0" style={{ backgroundColor: slice.color }} />
              <span className="font-semibold text-gray-700 dark:text-gray-300">{slice.label}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-bold text-gray-950 dark:text-gray-50">{slice.value}</span>
              <span className="text-gray-400 dark:text-gray-500 font-semibold">{slice.percentage}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

PieChartWrapper.displayName = "PieChartWrapper";
