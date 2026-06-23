import React from 'react';

interface StepIndicatorProps {
  currentStep: number;
}

const STEPS = [
  { id: 1, title: 'Exam Details' },
  { id: 2, title: 'Core Knowledge' },
  { id: 3, title: 'Rubric Intelligence' }
];

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <div className="mb-10 bg-white p-6 rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex items-center justify-between relative">
      <div className="absolute top-1/2 left-10 right-10 h-1 bg-gray-100 -z-10 -translate-y-1/2 rounded-full">
        <div 
          className="h-full bg-brand-primary transition-all duration-500 rounded-full" 
          style={{ width: `${((currentStep - 1) / (STEPS.length - 1)) * 100}%` }}
        />
      </div>
      
      {STEPS.map(step => (
        <div key={step.id} className="flex flex-col items-center gap-2 bg-white px-4">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold border-2 transition-colors ${
            step.id < currentStep ? 'bg-brand-primary border-brand-primary text-white' :
            step.id === currentStep ? 'bg-brand-surface border-brand-primary text-brand-dark' :
            'bg-white border-gray-200 text-gray-400'
          }`}>
            {step.id < currentStep ? '✓' : step.id}
          </div>
          <span className={`text-sm font-semibold ${step.id <= currentStep ? 'text-brand-dark' : 'text-gray-400'}`}>
            {step.title}
          </span>
        </div>
      ))}
    </div>
  );
}
