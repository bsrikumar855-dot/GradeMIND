'use client';

import React, { useState, useEffect, Suspense } from 'react';
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
  FileCheck2,
  AlertCircle
} from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';
import { MagicBentoCard, ShimmerBadge, AnimatedList, AnimatedListItem } from '@/components/ui';
import { JobProgressState } from '@/components/ui/job-progress-state';

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

  const jobIdParam = searchParams.get('job_id') || searchParams.get('jobId') || 'demo_job_a';

  if (!idsStr) {
    return (
      <div className="flex-1 flex flex-col space-y-6 text-left w-full">
        <div className="flex items-center justify-between border-b border-slate-200/80 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <ShimmerBadge variant="emerald">Evaluation Engine</ShimmerBadge>
              <span className="text-slate-400">•</span>
              <span className="text-xs font-bold text-slate-700">Autonomous Workflow</span>
            </div>
            <h1 className="text-2xl font-serif font-extrabold text-slate-900 tracking-tight mt-1">
              Active Evaluation Job Monitor
            </h1>
            <p className="text-xs font-medium text-slate-600">
              Live evaluation state, HTR transcription status, and progress preservation cache metrics.
            </p>
          </div>
        </div>

        <JobProgressState jobId={jobIdParam} />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col justify-between space-y-5 text-left w-full">
      
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-forest-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <ShimmerBadge variant="emerald">Evaluation Engine</ShimmerBadge>
            <span className="text-forest-300">•</span>
            <span className="text-xs font-bold text-forest-700">Autonomous Workflow</span>
          </div>
          <h1 className="text-2xl font-serif font-extrabold text-forest-900 tracking-tight mt-1">
            AI Evaluation Execution
          </h1>
          <p className="text-xs font-medium text-forest-600">
            Processing candidate submissions through 6 autonomous agent verification stages.
          </p>
        </div>

        <div className="px-4 py-2 rounded-lg bg-forest-900 text-white text-right shrink-0">
          <span className="text-[10px] font-bold uppercase text-forest-300 block tracking-wider">Est. Completion</span>
          <span className="text-sm font-extrabold text-forest-400">
            {isComplete ? 'Execution Complete' : estimatedSeconds !== null ? `~${estimatedSeconds}s remaining` : 'Calculating...'}
          </span>
        </div>
      </div>

      {/* Progress Track Card */}
      <MagicBentoCard showBeam={!isComplete} className="p-6 space-y-3">
        <div className="flex justify-between items-center text-xs font-bold text-forest-950">
          <span className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-forest-600 animate-pulse" /> Overall Pipeline Progress
          </span>
          <span className="text-forest-700 font-extrabold text-sm">{Math.round(progress)}%</span>
        </div>

        <div className="w-full h-3 bg-forest-50 rounded-full overflow-hidden border border-forest-200/60">
          <div 
            className="h-full rounded-full bg-forest-500 transition-all duration-500"
            style={{ width: `${Math.max(progress, 3)}%` }}
          />
        </div>
      </MagicBentoCard>

      {/* 6 AI Agent Timeline using AnimatedList inside MagicBentoCard */}
      <MagicBentoCard className="p-6 space-y-5">
        <h2 className="text-sm font-serif font-extrabold text-forest-950 flex items-center gap-2">
          <Brain className="w-4 h-4 text-forest-700" /> Multi-Agent Workflow Sequence
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent, index) => {
            const isFinished = isComplete || index < currentAgentIndex;
            const isActive = !isComplete && index === currentAgentIndex;

            return (
              <div 
                key={agent.id}
                className={`p-4 rounded-xl border transition-all flex flex-col justify-between space-y-3 ${
                  isFinished 
                    ? 'bg-forest-50 border-forest-200 text-forest-950' 
                    : isActive 
                    ? 'bg-forest-900 text-white border-forest-950 shadow-md' 
                    : 'bg-white border-forest-200/60 text-forest-500'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-extrabold text-xs ${
                    isFinished 
                      ? 'bg-forest-700 text-white' 
                      : isActive 
                      ? 'bg-forest-400 text-forest-950' 
                      : 'bg-forest-100 text-forest-600'
                  }`}>
                    {isFinished ? <CheckCircle2 className="w-4 h-4" /> : agent.id}
                  </div>

                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                    isFinished 
                      ? 'bg-forest-100 text-forest-900' 
                      : isActive 
                      ? 'bg-forest-500/20 text-forest-300' 
                      : 'bg-forest-50 text-forest-500'
                  }`}>
                    {isFinished ? 'Completed' : isActive ? 'Executing...' : 'Queued'}
                  </span>
                </div>

                <div>
                  <h3 className={`text-xs font-bold ${isActive ? 'text-white' : 'text-forest-950'}`}>{agent.name}</h3>
                  <p className={`text-[11px] mt-0.5 leading-snug ${isActive ? 'text-forest-200' : 'text-forest-600'}`}>{agent.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Completion CTA */}
        {isComplete && (
          <div className="pt-5 border-t border-forest-100 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-forest-100 text-forest-700 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-forest-950">Evaluation Finished!</h4>
                <p className="text-[11px] text-forest-600">Scorecard reports and annotated answer script are compiled.</p>
              </div>
            </div>

            <button
              onClick={() => router.push(`/results?submissionId=${submissionIds[0]}`)}
              className="w-full sm:w-auto px-6 py-2.5 bg-forest-900 hover:bg-forest-800 text-white font-bold text-xs rounded-lg transition-colors flex items-center justify-center gap-2 shadow-xs"
            >
              <span>View Results Breakdown</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </MagicBentoCard>

    </div>
  );
}

export default function EvaluationPage() {
  return (
    <Suspense fallback={
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="w-8 h-8 border-3 border-forest-600 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <EvaluationContent />
    </Suspense>
  );
}
