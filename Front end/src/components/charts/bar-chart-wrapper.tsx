import * as React from "react";
import { cn } from "@/utils/cn";

export interface BarChartData {
  label: string;
  value: number;
  secondaryValue?: number;
  color?: string;
  secondaryColor?: string;
}

export interface BarChartWrapperProps {
  data: BarChartData[];
  height?: number;
  className?: string;
  yAxisLabel?: string;
}

export const BarChartWrapper: React.FC<BarChartWrapperProps> = ({
  data,
  height = 200,
  className,
  yAxisLabel,
}) => {
  const maxValue = React.useMemo(() => {
    let max = 1;
    data.forEach((item) => {
      const val = item.value + (item.secondaryValue || 0);
      if (val > max) max = val;
    });
    return Math.ceil(max * 1.15); // Add 15% top padding
  }, [data]);

  // Generate 4 vertical grid intervals
  const gridLines = [0.25, 0.5, 0.75, 1.0];

  return (
    <div className={cn("flex flex-col w-full", className)}>
      <div className="flex flex-1 items-end relative gap-4" style={{ height: height }}>
        {/* Y-Axis scale tags */}
        <div className="absolute left-0 top-0 bottom-0 flex flex-col justify-between text-[10px] font-bold text-gray-400 w-10 pointer-events-none select-none z-10">
          <span>{maxValue}</span>
          <span>{Math.round(maxValue * 0.75)}</span>
          <span>{Math.round(maxValue * 0.5)}</span>
          <span>{Math.round(maxValue * 0.25)}</span>
          <span>0</span>
        </div>

        {/* Gridlines */}
        <div className="absolute inset-y-0 left-10 right-0 flex flex-col justify-between pointer-events-none select-none border-l border-b border-gray-200 dark:border-gray-800">
          {gridLines.map((ratio, index) => (
            <div
              key={index}
              className="w-full border-t border-dashed border-gray-150 dark:border-gray-800/80"
              style={{ height: `${(1 - ratio) * 100}%` }}
            />
          ))}
        </div>

        {/* Bar Columns Container */}
        <div className="flex-1 flex justify-around items-end h-full ml-10 relative z-10">
          {data.map((item, idx) => {
            const primaryHeight = `${(item.value / maxValue) * 100}%`;
            const secondaryHeight = item.secondaryValue
              ? `${(item.secondaryValue / maxValue) * 100}%`
              : "0%";

            return (
              <div key={idx} className="flex flex-col items-center group w-full max-w-[48px] px-1 hover:bg-gray-50/50 dark:hover:bg-gray-900/10 rounded-t-lg transition-colors">
                {/* Tooltip Overlay */}
                <div className="absolute bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 bg-gray-900 text-white text-[10px] px-2 py-1.5 rounded-lg shadow-md font-semibold select-none flex flex-col gap-0.5">
                  <span className="text-gray-400">{item.label}</span>
                  <span>Value: {item.value}</span>
                  {item.secondaryValue !== undefined && (
                    <span>Secondary: {item.secondaryValue}</span>
                  )}
                </div>

                {/* The Bar Stack */}
                <div className="w-full flex flex-col justify-end items-center gap-0.5 h-full pb-0.5">
                  {item.secondaryValue !== undefined && item.secondaryValue > 0 && (
                    <div
                      className={cn("w-full rounded-t-md transition-all duration-300", item.secondaryColor || "bg-indigo-500")}
                      style={{ height: secondaryHeight }}
                    />
                  )}
                  <div
                    className={cn(
                      "w-full rounded-t-md transition-all duration-300",
                      item.secondaryValue ? "rounded-t-none" : "rounded-t-md",
                      item.color || "bg-blue-600"
                    )}
                    style={{ height: primaryHeight }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* X-Axis labels */}
      <div className="flex justify-around ml-10 border-t border-gray-200 dark:border-gray-800 pt-2 text-[10px] font-bold text-gray-400 tracking-wide select-none">
        {data.map((item, index) => (
          <span key={index} className="w-full max-w-[48px] text-center truncate px-0.5" title={item.label}>
            {item.label}
          </span>
        ))}
      </div>

      {yAxisLabel && (
        <span className="text-[10px] font-bold text-gray-400 text-center mt-3 uppercase tracking-wider">
          {yAxisLabel}
        </span>
      )}
    </div>
  );
};

BarChartWrapper.displayName = "BarChartWrapper";
