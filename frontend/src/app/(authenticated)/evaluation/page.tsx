'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter, useSearchParams } from 'next/navigation';
import { 
  CheckCircle2, 
  XCircle, 
  ChevronRight, 
  Sparkles, 
  Activity, 
  Clock,
  Brain,
  Zap,
  ArrowRight,
  ShieldCheck,
  FileCheck2
} from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';

const agents = [
  { id: 1, name: 'OCR Agent', desc: 'Rasterizing document & extracting text/handwriting' },
  { id: 2, name: 'Understanding Agent', desc: 'Parsing question intent & academic domain concepts' },
  { id: 3, name: 'Evaluation Agent', desc: 'Running 120B LLM scoring against marking scheme' },
  { id: 4, name: 'Fairness Agent', desc: 'Auditing score consistency & removing bias' },
  { id: 5, name: 'Feedback Agent', desc: 'Generating strengths, weaknesses & study recommendations' },
  { id: 6, name: 'Report Agent', desc: 'Compiling PDF report card & scorecards' },
];

function EvaluationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idsStr = searchParams.get('ids');
  
  const [submissionIds, setSubmissionIds] = useState<string[]>([]);
  const [submissions, setSubmissions] = useState<Record<string, any>>({});
  const [progress, setProgress] = useState(0);
  const [targetProgress, setTargetProgress] = useState(0);
  const [estimatedSeconds, setEstimatedSeconds] = useState<number | null>(null);
  const [currentAgentIndex, setCurrentAgentIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [loadError, setLoadError] = useState('');

  const submissionsRef = React.useRef(submissions);
  useEffect(() => {
    submissionsRef.current = submissions;
  }, [submissions]);

  useEffect(() => {
    if (idsStr) {
      const ids = idsStr.split(',').filter(Boolean);
      setSubmissionIds(ids);
      if (ids.length > 0) {
        setEstimatedSeconds(Math.max(10, ids.length * 5));
      }
    }
  }, [idsStr]);

  useEffect(() => {
    if (isComplete || estimatedSeconds === null) return;
    const timer = setInterval(() => {
      setEstimatedSeconds((prev) => (prev !== null && prev > 1 ? prev - 1 : prev));
    }, 1000);
    return () => clearInterval(timer);
  }, [isComplete, estimatedSeconds]);

  useEffect(() => {
    if (isComplete) return;
    const timer = setInterval(() => {
      setProgress((prev) => {
        if (targetProgress > 0 && prev < targetProgress + 12 && prev < 98) {
          return Math.round((prev + 0.5) * 10) / 10;
        }
        return prev;
      });
    }, 400);
    return () => clearInterval(timer);
  }, [targetProgress, isComplete]);

  // Polling backend status
  useEffect(() => {
    if (submissionIds.length === 0) return;

    let active = true;

    const fetchStatuses = async () => {
      try {
        const nextSubmissions: Record<string, any> = { ...submissionsRef.current };
        let updatedAny = false;

        await Promise.all(
          submissionIds.map(async (id) => {
            const current = submissionsRef.current[id];
            if (current && (current.status === 'COMPLETED' || current.status === 'FAILED')) {
              return;
            }

            try {
              const res = await SubmissionService.getStatus(id);
              if (res.success && res.data) {
                if (!current || !current.student_name) {
                  const detailsRes = await SubmissionService.getSubmissionById(id);
                  nextSubmissions[id] = {
                    ...res.data,
                    student_name: detailsRes.success ? detailsRes.data.student_name : `Student (${id.substring(0, 4)})`,
                    student_roll_number: detailsRes.success ? detailsRes.data.student_roll_number : 'N/A'
                  };
                } else {
                  nextSubmissions[id] = { ...current, ...res.data };
                }
                updatedAny = true;
              }
            } catch (err) {
              console.error(`Failed to poll status for ${id}:`, err);
              nextSubmissions[id] = {
                ...(current || { id }),
                status: 'FAILED',
                error_message: 'Evaluation failed on backend.'
              };
              updatedAny = true;
            }
          })
        );

        if (!active) return;
        if (updatedAny) setSubmissions(nextSubmissions);

        const subList = Object.values(nextSubmissions);
        if (subList.length === submissionIds.length) {
          const allCompleted = subList.every((s: any) => s.status === 'COMPLETED');
          const anyFailed = subList.some((s: any) => s.status === 'FAILED');

          if (allCompleted) {
            setProgress(100);
            setTargetProgress(100);
            setCurrentAgentIndex(5);
            setIsComplete(true);
            return;
          }

          if (anyFailed && subList.every((s: any) => s.status === 'COMPLETED' || s.status === 'FAILED')) {
            setIsComplete(true);
            return;
          }

          let minStep = 6;
          subList.forEach((s: any) => {
            let step = 0;
            const status = s.status || '';
            const ocrStatus = s.ocr_status || '';

            if (status === 'COMPLETED') step = 6;
            else if (status === 'EVALUATION_COMPLETE') step = 5;
            else if (status === 'EVALUATING') step = 3;
            else if (ocrStatus === 'COMPLETED' || status === 'OCR_COMPLETE') step = 2;
            else if (ocrStatus === 'PROCESSING' || status === 'PROCESSING') step = 1;

            if (step < minStep) minStep = step;
          });

          const calculatedProgress = Math.round((minStep / 6) * 100);
          setTargetProgress(calculatedProgress);
          setCurrentAgentIndex(Math.min(minStep, 5));
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    fetchStatuses();
    const interval = setInterval(fetchStatuses, 1500);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [submissionIds]);

  if (!idsStr) {
    return (
      <div className="max-w-2xl mx-auto mt-16 p-8 glass-card rounded-3xl text-center space-y-4">
        <XCircle className="w-12 h-12 text-rose-500 mx-auto" />
        <h2 className="text-xl font-bold text-slate-900">No Submissions Selected</h2>
        <p className="text-slate-500 text-sm">Please upload an exam answer sheet to launch the evaluation pipeline.</p>
        <button 
          onClick={() => router.push('/upload')} 
          className="px-6 py-2.5 bg-slate-900 text-white font-bold text-sm rounded-xl"
        >
          Go to Upload Center
        </button>
      </div>
    );
  }

  const subList = Object.values(submissions);
  const isFailed = subList.some((s: any) => s.status === 'FAILED');

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16">
      
      {/* Top Banner */}
      <div className="calm-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold uppercase tracking-wider mb-2">
            Pipeline Processing
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Evaluation Pipeline Active
          </h1>
          <p className="text-slate-600 text-sm mt-1">
            Processing candidate submissions through multi-stage OCR, criteria evaluation, and verification.
          </p>
        </div>

        {/* Countdown ETA Badge */}
        <div className="px-4 py-2 rounded-lg bg-slate-50 border border-slate-200 text-right">
          <span className="text-[10px] font-bold uppercase text-slate-500 block tracking-wider">Est. Remaining</span>
          <span className="text-lg font-bold text-slate-900">
            {isComplete ? 'Complete' : estimatedSeconds !== null ? `~${estimatedSeconds}s` : 'Calculating...'}
          </span>
        </div>
      </div>

      {/* Progress Bar Card */}
      <div className="calm-card p-6 space-y-4">
        <div className="flex justify-between items-center text-sm font-semibold text-slate-900">
          <span className="flex items-center gap-2">
            Overall Pipeline Progress
          </span>
          <span className="text-slate-900 font-bold text-base">{Math.round(progress)}%</span>
        </div>

        {/* Progress Track */}
        <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
          <div 
            className="h-full rounded-full bg-slate-900 transition-all duration-500"
            style={{ width: `${Math.max(progress, 3)}%` }}
          />
        </div>
      </div>

      {/* 6 AI Agent Timeline */}
      <div className="glass-card rounded-3xl p-8 space-y-6">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <Brain className="w-5 h-5 text-emerald-600" /> Multi-Agent Workflow Sequence
        </h2>

        <div className="space-y-4">
          {agents.map((agent, index) => {
            const isFinished = isComplete || index < currentAgentIndex;
            const isActive = !isComplete && index === currentAgentIndex;

            return (
              <div 
                key={agent.id}
                className={`p-5 rounded-2xl border transition-all duration-300 flex items-center justify-between gap-4 ${
                  isFinished 
                    ? 'bg-emerald-50/60 border-emerald-200/80 text-slate-900' 
                    : isActive 
                    ? 'bg-slate-900 text-white border-slate-900 shadow-xl shadow-slate-900/10 scale-[1.01]' 
                    : 'bg-slate-50/50 text-slate-400 border-slate-200/50'
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${
                    isFinished 
                      ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20' 
                      : isActive 
                      ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/30 animate-pulse' 
                      : 'bg-slate-200 text-slate-500'
                  }`}>
                    {isFinished ? <CheckCircle2 className="w-5 h-5" /> : agent.id}
                  </div>

                  <div>
                    <h3 className={`text-sm font-bold ${isActive ? 'text-white' : 'text-slate-900'}`}>{agent.name}</h3>
                    <p className={`text-xs mt-0.5 ${isActive ? 'text-slate-300' : 'text-slate-500'}`}>{agent.desc}</p>
                  </div>
                </div>

                <div>
                  {isFinished && (
                    <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-600 text-xs font-bold border border-emerald-500/20">
                      Completed
                    </span>
                  )}
                  {isActive && (
                    <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold border border-emerald-500/30 animate-pulse">
                      Executing...
                    </span>
                  )}
                  {!isFinished && !isActive && (
                    <span className="px-3 py-1 rounded-full bg-slate-200/60 text-slate-400 text-xs font-semibold">
                      Queued
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Completion CTA */}
        {isComplete && (
          <div className="pt-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">Evaluation Finished!</h4>
                <p className="text-xs text-slate-500">Scorecard reports and annotated answer sheet are compiled.</p>
              </div>
            </div>

            <button
              onClick={() => router.push(`/results?submissionId=${submissionIds[0]}`)}
              className="w-full sm:w-auto px-8 py-3.5 bg-slate-900 hover:bg-slate-800 text-white font-black text-sm rounded-xl transition-all shadow-xl shadow-slate-900/20 flex items-center justify-center gap-2"
            >
              View Results Breakdown <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

    </div>
  );
}

export default function EvaluationPage() {
  return (
    <Suspense fallback={
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <EvaluationContent />
    </Suspense>
  );
}
