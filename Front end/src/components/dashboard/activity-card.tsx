import * as React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { cn } from "@/utils/cn";

export interface ActivityItem {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  icon?: React.ReactNode;
}

export interface ActivityCardProps {
  title?: string;
  items: ActivityItem[];
  className?: string;
}

export const ActivityCard: React.FC<ActivityCardProps> = ({
  title = "Recent Activity",
  items,
  className,
}) => {
  return (
    <Card className={cn("flex flex-col h-full", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-bold text-gray-950 dark:text-gray-50">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto pr-2">
        {items.length === 0 ? (
          <div className="flex h-40 items-center justify-center text-sm text-gray-500 dark:text-gray-400">
            No recent activity
          </div>
        ) : (
          <div className="relative border-l border-gray-150 dark:border-gray-800 ml-3 pl-6 space-y-6">
            {items.map((item) => (
              <div key={item.id} className="relative group">
                {/* Visual Bullet indicator */}
                <span className="absolute -left-[31px] top-1.5 flex h-4.5 w-4.5 items-center justify-center rounded-full border border-gray-250 bg-white text-gray-500 dark:border-gray-850 dark:bg-gray-950 dark:text-gray-450 group-hover:scale-105 transition-transform">
                  {item.icon || <div className="h-1.5 w-1.5 rounded-full bg-blue-600" />}
                </span>

                <div className="space-y-1">
                  <div className="flex items-center justify-between gap-4">
                    <h4 className="text-sm font-semibold text-gray-950 dark:text-gray-50">
                      {item.title}
                    </h4>
                    <span className="text-[10px] text-gray-500 dark:text-gray-400 shrink-0 font-medium">
                      {item.timestamp}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

ActivityCard.displayName = "ActivityCard";
