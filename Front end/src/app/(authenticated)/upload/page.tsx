'use client';

import React, { useState, useCallback } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';

type FileType = 'questionPaper' | 'answerKey' | 'studentSheets';

export default function UploadCenter() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [files, setFiles] = useState<Record<FileType, File[]>>({
    questionPaper: [],
    answerKey: [],
    studentSheets: [],
  });
  const [isDragging, setIsDragging] = useState(false);

  const steps = [
    { id: 1, title: 'Question Paper', key: 'questionPaper' as FileType, desc: 'Upload the blank question paper (PDF)' },
    { id: 2, title: 'Answer Key', key: 'answerKey' as FileType, desc: 'Upload the correct answers or rubric' },
    { id: 3, title: 'Student Sheets', key: 'studentSheets' as FileType, desc: 'Upload scanned student answer sheets' },
  ];

  const currentStepData = steps[currentStep - 1];

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      setFiles(prev => ({
        ...prev,
        [currentStepData.key]: [...prev[currentStepData.key], ...droppedFiles]
      }));
    }
  }, [currentStepData.key]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      setFiles(prev => ({
        ...prev,
        [currentStepData.key]: [...prev[currentStepData.key], ...selectedFiles]
      }));
    }
  };

  const removeFile = (fileType: FileType, index: number) => {
    setFiles(prev => ({
      ...prev,
      [fileType]: prev[fileType].filter((_, i) => i !== index)
    }));
  };

  const canProceed = files[currentStepData.key].length > 0;

  return (
    <div className="flex flex-col min-h-full">
      <header className="h-20 bg-white/50 backdrop-blur-md border-b border-gray-100/50 flex items-center px-8 sticky top-0 z-10">
        <h1 className="text-2xl font-bold text-brand-dark">New Evaluation Setup</h1>
      </header>

      <div className="flex-1 p-4 lg:p-6 w-full max-w-screen-2xl mx-auto flex flex-col gap-6">
          {/* Progress Tracker */}
          <div className="mb-10 bg-white p-6 rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex items-center justify-between relative">
            <div className="absolute top-1/2 left-10 right-10 h-1 bg-gray-100 -z-10 -translate-y-1/2 rounded-full">
               <div 
                 className="h-full bg-brand-primary transition-all duration-500 rounded-full" 
                 style={{ width: `${((currentStep - 1) / 2) * 100}%` }}
               />
            </div>
            
            {steps.map(step => (
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

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
            
            {/* Left Side: Illustration & Instructions */}
            <div className="bg-brand-secondary rounded-2xl flex flex-col items-center justify-center text-center relative overflow-hidden border border-brand-primary/20 min-h-[400px]">
              
              {/* Illustration in the Background */}
              <div className="absolute inset-0 w-full h-full z-0 pointer-events-none opacity-90 overflow-hidden">
                <Image 
                  src="/images/upload-illustration.png" 
                  alt="Upload Illustration" 
                  fill
                  className="object-cover object-center mix-blend-multiply scale-[1.4]"
                  priority
                />
              </div>
              
              <div className="relative z-10 bg-white/90 backdrop-blur-lg p-6 rounded-2xl border border-white shadow-xl mt-auto mb-10 mx-6 w-11/12 max-w-sm">
                <h3 className="text-2xl font-extrabold text-black mb-2">Step {currentStep}: {currentStepData.title}</h3>
                <p className="text-black/80 font-medium text-lg">{currentStepData.desc}</p>
              </div>
            </div>

            {/* Right Side: Upload Zone */}
            <div className="flex flex-col h-full">
              <div 
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`flex-1 bg-white rounded-2xl border-2 border-dashed flex flex-col items-center justify-center p-12 transition-all duration-200 ${
                  isDragging ? 'border-brand-primary bg-brand-surface/30' : 'border-gray-200 hover:border-brand-primary/50 hover:bg-gray-50'
                }`}
              >
                <div className="w-16 h-16 bg-brand-secondary rounded-full flex items-center justify-center text-brand-primary mb-4">
                  <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                </div>
                <h3 className="text-lg font-bold text-brand-dark mb-2">Drag & Drop files here</h3>
                <p className="text-sm text-gray-500 mb-6">or</p>
                <label className="bg-brand-primary text-white px-6 py-2.5 rounded-xl font-medium cursor-pointer hover:bg-opacity-90 active:scale-95 transition-all shadow-sm">
                  Browse Files
                  <input type="file" multiple className="hidden" onChange={handleFileInput} />
                </label>
                <p className="text-xs text-gray-400 mt-6">Supports PDF, JPG, PNG (Max 50MB)</p>
              </div>

              {/* File Preview Area */}
              {files[currentStepData.key].length > 0 && (
                <div className="mt-6 bg-white p-6 rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 max-h-48 overflow-y-auto">
                  <h4 className="text-sm font-semibold text-brand-dark mb-3">Uploaded Files ({files[currentStepData.key].length})</h4>
                  <div className="space-y-2">
                    {files[currentStepData.key].map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-brand-background rounded-xl border border-gray-100">
                        <div className="flex items-center gap-3 overflow-hidden">
                          <svg className="w-5 h-5 text-brand-primary flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" /></svg>
                          <span className="text-sm font-medium text-brand-dark truncate">{file.name}</span>
                          <span className="text-xs text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                        </div>
                        <button onClick={() => removeFile(currentStepData.key, idx)} className="text-red-400 hover:text-red-600 p-1">
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-8 flex justify-between items-center bg-white p-6 rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
            <button 
              onClick={() => setCurrentStep(prev => Math.max(1, prev - 1))}
              disabled={currentStep === 1}
              className="px-6 py-3 rounded-xl font-medium text-brand-dark bg-gray-50 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Back
            </button>
            
            {currentStep < 3 ? (
              <button 
                onClick={() => setCurrentStep(prev => Math.min(3, prev + 1))}
                disabled={!canProceed}
                className="px-8 py-3 rounded-xl font-medium text-white bg-brand-primary hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all shadow-md"
              >
                Continue to Next Step
              </button>
            ) : (
              <button 
                onClick={() => router.push('/evaluation')}
                disabled={!canProceed}
                className="px-10 py-4 rounded-xl font-bold text-white bg-brand-accent hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all shadow-[0_10px_30px_rgba(91,141,239,0.3)] flex items-center gap-2 text-lg"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                Start AI Evaluation
              </button>
            )}
          </div>

      </div>
    </div>
  );
}
