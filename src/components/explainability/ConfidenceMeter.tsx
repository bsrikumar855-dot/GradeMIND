// src/components/explainability/ConfidenceMeter.tsx
import React from 'react';

type Props = {
  confidence: number;
};

export default function ConfidenceMeter({ confidence }: Props) {
  const getColor = () => {
    if (confidence >= 80) return 'bg-green-500';
    if (confidence >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="flex-1 w-full flex flex-col justify-center">
      <h3 className="text-3xl lg:text-5xl font-extrabold text-brand-dark mb-10">AI Confidence Score</h3>
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 lg:gap-10">
        <div className="flex-1 w-full bg-gray-100 rounded-2xl h-10 lg:h-14 p-1.5 border border-gray-200/50 shadow-inner">
          <div
            className={`${getColor()} h-full rounded-xl transition-all duration-1000 ease-out shadow-sm`}
            style={{ width: `${confidence}%` }}
          />
        </div>
        <span className="text-5xl lg:text-7xl xl:text-8xl font-black text-brand-dark leading-none tracking-tight shrink-0">{confidence}%</span>
      </div>
    </div>
  );
}
