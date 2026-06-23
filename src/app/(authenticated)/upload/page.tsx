'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { StepIndicator } from '@/components/upload/StepIndicator';
import { ExamForm } from '@/components/upload/ExamForm';
import { DropzoneContainer } from '@/components/upload/DropzoneContainer';
import { RubricGrid } from '@/components/upload/RubricGrid';
import { UploadState, ExamDetails } from '@/components/upload/types';
import { ChevronRight, ChevronLeft, CheckCircle2 } from 'lucide-react';

const INITIAL_EXAM_DETAILS: ExamDetails = {
  title: '',
  subject: '',
  total_marks: 0,
  exam_date: new Date().toISOString().split('T')[0],
};

export default function UploadWizard() {
  const router = useRouter();
  const [state, setState] = useState<UploadState>({
    step: 1,
    examDetails: INITIAL_EXAM_DETAILS,
    files: {
      questionPaper: [],
      answerKey: [],
    },
    rubric: [],
  });

  const handleNext = () => setState(prev => ({ ...prev, step: Math.min(3, prev.step + 1) }));
  const handleBack = () => setState(prev => ({ ...prev, step: Math.max(1, prev.step - 1) }));
  
  const handleComplete = () => {
    // Navigate to evaluation/demo or dashboard when completed
    router.push('/evaluation/demo');
  };

  const isStepValid = () => {
    switch (state.step) {
      case 1:
        return state.examDetails.title.trim() !== '' && 
               state.examDetails.subject.trim() !== '' && 
               state.examDetails.total_marks > 0;
      case 2:
        return state.files.questionPaper.length > 0 && 
               state.files.answerKey.length > 0;
      case 3:
        return state.rubric.length > 0 && state.rubric.every(r => r.label.trim() !== '');
      default:
        return false;
    }
  };

  return (
    <div className="flex flex-col min-h-full bg-brand-background">
      <header className="h-20 bg-white/50 backdrop-blur-md border-b border-brand-surface/50 flex items-center px-8 sticky top-0 z-10 justify-between">
        <h1 className="text-2xl font-bold text-brand-dark">New Evaluation Setup</h1>
        {state.step === 3 && isStepValid() && (
          <div className="flex items-center gap-2 text-green-600 bg-green-50 px-4 py-2 rounded-lg font-semibold text-sm border border-green-200">
            <CheckCircle2 className="w-5 h-5" />
            Ready for Analysis
          </div>
        )}
      </header>

      <div className="flex-1 p-4 lg:p-6 w-full max-w-screen-2xl mx-auto flex flex-col gap-6">
        <StepIndicator currentStep={state.step} />

        <div className="flex-1 w-full bg-white rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-100 overflow-hidden">
          {state.step === 1 && (
            <ExamForm 
              details={state.examDetails} 
              onChange={(details) => setState(prev => ({ ...prev, examDetails: details }))} 
            />
          )}
          
          {state.step === 2 && (
            <DropzoneContainer 
              files={state.files} 
              onChange={(files) => setState(prev => ({ ...prev, files }))} 
            />
          )}
          
          {state.step === 3 && (
            <RubricGrid 
              rubric={state.rubric} 
              onChange={(rubric) => setState(prev => ({ ...prev, rubric }))} 
            />
          )}
        </div>

        <div className="mt-8 flex justify-between items-center bg-white p-6 rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-100">
          <button 
            onClick={handleBack}
            disabled={state.step === 1}
            className="flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-brand-dark bg-gray-50 hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
            Back
          </button>
          
          {state.step < 3 ? (
            <button 
              onClick={handleNext}
              disabled={!isStepValid()}
              className="flex items-center gap-2 px-8 py-3 rounded-xl font-bold text-white bg-brand-primary hover:bg-brand-dark disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-md"
            >
              Continue
              <ChevronRight className="w-5 h-5" />
            </button>
          ) : (
            <button 
              onClick={handleComplete}
              disabled={!isStepValid()}
              className="flex items-center gap-2 px-10 py-3 rounded-xl font-bold text-white bg-brand-accent hover:bg-opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-[0_4px_14px_rgba(91,141,239,0.4)] hover:shadow-[0_6px_20px_rgba(91,141,239,0.6)]"
            >
              Complete Setup
              <CheckCircle2 className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
