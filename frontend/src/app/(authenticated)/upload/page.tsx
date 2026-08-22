'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  UploadCloud, 
  FileText, 
  Trash2, 
  Sparkles, 
  AlertCircle
} from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';

export default function UploadCenter() {
  const router = useRouter();

  const [paper, setPaper] = useState<File | null>(null);
  const [answers, setAnswers] = useState<File | null>(null);
  const [scheme, setScheme] = useState<File | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const handleStartEvaluation = async () => {
    setSubmitError('');
    if (!paper || !answers || !scheme) {
      setSubmitError('Please upload all three required files: Question Paper, Answer Sheet, and Marking Scheme.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await SubmissionService.gradeV2(paper, answers, scheme);
      if (res.job_id) {
        router.push(`/results?job_id=${res.job_id}`);
      } else {
        throw new Error('Failed to start grading job: No job_id returned.');
      }
    } catch (err: any) {
      console.error('Submission failed:', err);
      setSubmitError(err.message || 'An error occurred during evaluation setup.');
      setIsSubmitting(false);
    }
  };

  const FileDropzone = ({ 
    label, 
    file, 
    setFile, 
    accept 
  }: { 
    label: string, 
    file: File | null, 
    setFile: (f: File | null) => void,
    accept: string
  }) => (
    <div className="space-y-2">
      <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">{label} *</label>
      
      {!file ? (
        <div 
          className="border-2 border-dashed border-slate-300 hover:border-emerald-500/50 bg-slate-50/50 rounded-3xl p-6 text-center transition-all duration-300"
        >
          <UploadCloud className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
          <h4 className="text-sm font-bold text-slate-900">Upload {label}</h4>
          
          <label className="mt-3 inline-block px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl cursor-pointer transition-all">
            Browse File
            <input 
              type="file" 
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setFile(e.target.files[0]);
                }
              }} 
              accept={accept} 
              className="hidden" 
            />
          </label>
        </div>
      ) : (
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-slate-900 text-xs font-semibold">
          <div className="flex items-center gap-3">
            <FileText className="w-4 h-4 text-emerald-600" />
            <span>{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
          </div>
          <button onClick={() => setFile(null)} className="text-rose-500 hover:text-rose-700 p-1">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      <div className="glass-card rounded-3xl p-8 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white shadow-2xl border border-slate-700/50">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-wider mb-2">
          <Sparkles className="w-3.5 h-3.5" /> GradeMIND v2 Engine
        </div>
        <h1 className="text-3xl font-black text-white tracking-tight">
          Upload Answer Script
        </h1>
        <p className="text-slate-300 text-sm mt-1">
          Upload a Question Paper, an Answer Sheet, and a Marking Scheme (JSON) to evaluate a student's submission using the verified pipeline.
        </p>
      </div>

      <div className="glass-card rounded-3xl p-8 space-y-8">
        
        <FileDropzone 
          label="Question Paper (PDF/Image)" 
          file={paper} 
          setFile={setPaper} 
          accept="image/*,.pdf" 
        />

        <FileDropzone 
          label="Marking Scheme (JSON)" 
          file={scheme} 
          setFile={setScheme} 
          accept=".json" 
        />

        <FileDropzone 
          label="Student Answer Sheet (PDF/Image)" 
          file={answers} 
          setFile={setAnswers} 
          accept="image/*,.pdf" 
        />

        {submitError && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-xs font-bold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{submitError}</span>
          </div>
        )}

        <div className="flex justify-end pt-4 border-t border-slate-100">
          <button
            onClick={handleStartEvaluation}
            disabled={isSubmitting || !paper || !answers || !scheme}
            className={`px-8 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-black text-sm rounded-xl transition-all shadow-xl shadow-emerald-500/25 flex items-center gap-2 ${
              (isSubmitting || !paper || !answers || !scheme) ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Initiating Evaluation...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" /> Start Evaluation
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
