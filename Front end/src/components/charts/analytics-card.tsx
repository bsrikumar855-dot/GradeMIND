import React from 'react';

interface AnalyticsCardProps {
  title: string;
  value: string | number;
  trend?: {
    value: string | number;
    isPositive: boolean;
    label?: string;
  };
  icon?: React.ReactNode;
  variant?: 'default' | 'primary' | 'accent';
  className?: string;
  children?: React.ReactNode; // Slot for optional mini-charts (like sparklines)
}

export function AnalyticsCard({
  title,
  value,
  trend,
  icon,
  variant = 'default',
  className = '',
  children,
}: AnalyticsCardProps) {
  // Base styling using GradeMIND design system rules
  const baseClasses = "relative overflow-hidden rounded-2xl p-6 transition-all duration-300";
  // Custom soft shadow from the design system
  const shadowClass = "shadow-[0_4px_20px_rgba(47,90,58,0.05)]";
  
  // Variant backgrounds
  const variants = {
    default: `bg-[#FFFFFF] ${shadowClass} border border-gray-50/50`,
    primary: "bg-[#86B77B] text-white shadow-[0_10px_30px_rgba(134,183,123,0.3)]",
    accent: "bg-[#5B8DEF] text-white shadow-[0_10px_30px_rgba(91,141,239,0.3)]",
  };

  // Color mapping based on variant
  const textClasses = {
    default: {
      title: "text-[#6B7280]", // Muted secondary text
      value: "text-[#2F5A3A]", // GradeMIND Dark for strong hierarchy
      trendPositive: "text-[#2F5A3A] bg-[#EEF7E8]", // Secondary background for soft success
      trendNegative: "text-red-700 bg-red-50",
      trendLabel: "text-[#6B7280]",
      iconBg: "bg-[#EEF7E8] text-[#86B77B]", // Soft icon container
    },
    primary: {
      title: "text-white/80",
      value: "text-white",
      trendPositive: "text-white bg-white/20 backdrop-blur-sm",
      trendNegative: "text-white bg-red-500/30 backdrop-blur-sm",
      trendLabel: "text-white/70",
      iconBg: "bg-white/20 text-white backdrop-blur-sm",
    },
    accent: {
      title: "text-white/80",
      value: "text-white",
      trendPositive: "text-white bg-white/20 backdrop-blur-sm",
      trendNegative: "text-white bg-red-500/30 backdrop-blur-sm",
      trendLabel: "text-white/70",
      iconBg: "bg-white/20 text-white backdrop-blur-sm",
    }
  };

  const currentColors = textClasses[variant];

  return (
    <div className={`${baseClasses} ${variants[variant]} ${className} group hover:-translate-y-1`}>
      <div className="flex justify-between items-start mb-4 relative z-10">
        <div>
          <h3 className={`text-sm font-medium mb-1 ${currentColors.title}`}>
            {title}
          </h3>
          <div className={`text-3xl font-bold tracking-tight ${currentColors.value}`}>
            {value}
          </div>
        </div>
        {icon && (
          <div className={`p-3 rounded-xl ${currentColors.iconBg} transition-transform group-hover:scale-110`}>
            {icon}
          </div>
        )}
      </div>

      {(trend || children) && (
        <div className="mt-4 flex items-end justify-between relative z-10">
          {trend && (
            <div className="flex items-center gap-2">
              <span 
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${
                  trend.isPositive ? currentColors.trendPositive : currentColors.trendNegative
                }`}
              >
                {trend.isPositive ? '↑' : '↓'} {trend.value}
              </span>
              {trend.label && (
                <span className={`text-xs ${currentColors.trendLabel}`}>
                  vs {trend.label}
                </span>
              )}
            </div>
          )}
          {children && (
            <div className="flex-1 ml-4 h-12 w-full">
              {children}
            </div>
          )}
        </div>
      )}
      
      {/* Decorative background element for colored variants to add depth */}
      {variant !== 'default' && (
        <div className="absolute -right-8 -top-8 w-32 h-32 bg-white opacity-10 rounded-full blur-2xl transform group-hover:scale-150 transition-transform duration-700 pointer-events-none" />
      )}
    </div>
  );
}
