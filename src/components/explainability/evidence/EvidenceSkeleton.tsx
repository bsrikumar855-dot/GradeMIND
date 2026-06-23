'use client';

import React from 'react';

export default function EvidenceSkeleton() {
  return (
    <div className="flex flex-col lg:flex-row gap-6 lg:gap-8 w-full h-[600px] bg-white dark:bg-gray-900 rounded-[2rem] border border-gray-100 dark:border-gray-800 p-6 lg:p-10">
      {/* Sidebar Skeleton */}
      <div className="w-full lg:w-1/3 flex flex-col gap-4 border-r-0 lg:border-r border-gray-100 dark:border-gray-800 pr-0 lg:pr-6">
        <div className="h-8 w-3/4 bg-gray-200 dark:bg-gray-800 rounded-lg animate-pulse mb-4"></div>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 w-full bg-gray-100 dark:bg-gray-800 rounded-xl animate-pulse"></div>
        ))}
      </div>

      {/* Main Content Skeleton */}
      <div className="flex-1 flex flex-col gap-6 pl-0 lg:pl-2">
        <div className="h-8 w-1/2 bg-gray-200 dark:bg-gray-800 rounded-lg animate-pulse"></div>
        <div className="space-y-4 flex-1">
          <div className="h-4 w-full bg-gray-100 dark:bg-gray-800 rounded animate-pulse"></div>
          <div className="h-4 w-11/12 bg-gray-100 dark:bg-gray-800 rounded animate-pulse"></div>
          <div className="h-4 w-full bg-gray-100 dark:bg-gray-800 rounded animate-pulse"></div>
          <div className="h-4 w-4/5 bg-gray-100 dark:bg-gray-800 rounded animate-pulse"></div>
          <div className="h-4 w-full bg-gray-100 dark:bg-gray-800 rounded animate-pulse"></div>
        </div>
      </div>
    </div>
  );
}
