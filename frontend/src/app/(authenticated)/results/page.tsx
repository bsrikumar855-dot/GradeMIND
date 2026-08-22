'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { 
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  Sparkles,
  FileCheck2,
  XCircle,
  HelpCircle,
  Hash
} from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';

function ResultsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get('job_id');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [jobData, setJobData] = useState<any>(null);

  useEffect(() => {
    let interval: any = null;

    async function checkJob() {
      if (!jobId) {
        setError('No job_id provided.');
        setLoading(false);
        return;
      }

      try {
        const res = await SubmissionService.pollGradeJob(jobId);
        
        if (res.status === 'completed') {
          setJobData(res.report);
          setLoading(false);
          if (interval) clearInterval(interval);
        } else if (res.status === 'failed') {
          setError(res.error || 'Evaluation failed.');
          setLoading(false);
          if (interval) clearInterval(interval);
        }
      } catch (err: any) {
        console.error('Polling failed:', err);
        setError('Failed to retrieve evaluation job status.');
        setLoading(false);
        if (interval) clearInterval(interval);
      }
    }

    if (jobId) {
      checkJob();
      interval = setInterval(checkJob, 2000);
    } else {
      setLoading(false);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobId]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[65vh] space-y-4">
        <div className="w-10 h-10 border-4 border-slate-900 border-t-emerald-500 rounded-full animate-spin"></div>
        <p className="text-slate-500 font-bold text-xs">Waiting for AI Pipeline to complete...</p>
      </div>
    );
  }

  if (error || !jobData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh]">
        <AlertTriangle className="w-12 h-12 text-rose-500 mb-4" />
        <h2 className="text-lg font-bold text-slate-900">Oops! Something went wrong</h2>
        <p className="text-slate-500 text-sm mt-2">{error || 'Job data not found.'}</p>
        <button 
          onClick={() => router.push('/upload')} 
          className="mt-6 px-6 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-bold flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Upload
        </button>
      </div>
    );
  }

  const { questions, coverage, totals, provenance } = jobData;

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-20">
      
      {/* Header */}
      <div className="flex items-center gap-4">
        <button 
          onClick={() => router.push('/upload')}
          className="p-2.5 rounded-xl bg-white border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-500" /> Evaluation Report
          </h1>
          <p className="text-slate-500 text-sm font-medium mt-1">
            Job ID: {jobId}
          </p>
        </div>
      </div>

      {/* Totals Summary */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="p-4 rounded-3xl bg-slate-900 text-white flex flex-col justify-center">
          <p className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">Total Mark</p>
          <p className="text-3xl font-black">{totals?.total_awarded} <span className="text-lg text-slate-500 font-bold">/ {totals?.total_possible}</span></p>
        </div>
        <div className="p-4 rounded-3xl bg-white border border-slate-200">
          <p className="text-slate-500 text-[11px] font-bold uppercase tracking-wider mb-1">Scored</p>
          <p className="text-2xl font-black text-slate-900">{totals?.scored}</p>
        </div>
        <div className="p-4 rounded-3xl bg-white border border-slate-200">
          <p className="text-slate-500 text-[11px] font-bold uppercase tracking-wider mb-1">Routed</p>
          <p className="text-2xl font-black text-amber-600">{totals?.routed}</p>
        </div>
        <div className="p-4 rounded-3xl bg-white border border-slate-200">
          <p className="text-slate-500 text-[11px] font-bold uppercase tracking-wider mb-1">No Scheme</p>
          <p className="text-2xl font-black text-slate-900">{totals?.no_scheme}</p>
        </div>
        <div className="p-4 rounded-3xl bg-white border border-slate-200">
          <p className="text-slate-500 text-[11px] font-bold uppercase tracking-wider mb-1">Flagged</p>
          <p className="text-2xl font-black text-rose-600">{totals?.flagged}</p>
        </div>
      </div>

      {/* Coverage Section */}
      {coverage && coverage.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-3xl p-6">
          <h3 className="text-sm font-black text-amber-900 uppercase tracking-widest flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4" /> Coverage Notes
          </h3>
          <div className="space-y-4">
            {coverage.map((cov: any, idx: number) => (
              <div key={idx} className="bg-white/60 p-4 rounded-xl border border-amber-200/50">
                <p className="font-bold text-amber-900 text-sm mb-2">{cov[0]}</p>
                <ul className="list-disc list-inside space-y-1">
                  {cov[1].map((item: string, i: number) => (
                    <li key={i} className="text-xs text-amber-800">{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Questions List */}
      <div className="space-y-6">
        <h3 className="text-lg font-black text-slate-900">Per-Question Breakdown</h3>
        {questions?.map((q: any, i: number) => (
          <div key={i} className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-slate-200 text-slate-700 flex items-center justify-center font-black">
                  Q{q.question_number}
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                    {q.status === 'scored' && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                    {q.status === 'routed' && <AlertTriangle className="w-4 h-4 text-amber-500" />}
                    {q.status.includes('no scheme') && <HelpCircle className="w-4 h-4 text-slate-400" />}
                    {q.status.toUpperCase()}
                  </h4>
                  {q.routing_reason && (
                    <p className="text-xs font-bold text-amber-600 mt-0.5">Reason: {q.routing_reason}</p>
                  )}
                  {q.flagged && (
                    <p className="text-xs font-bold text-rose-600 mt-0.5">FLAGGED by safety boundaries</p>
                  )}
                </div>
              </div>
              {q.status === 'scored' && (
                <div className="text-right">
                  <p className="text-xl font-black text-slate-900">{q.mark} <span className="text-sm text-slate-400">/ {q.max_marks}</span></p>
                </div>
              )}
            </div>

            {q.value_points && q.value_points.length > 0 && (
              <div className="p-5 space-y-4">
                {q.value_points.map((vp: any, vpIdx: number) => (
                  <div key={vpIdx} className={`p-4 rounded-2xl border ${vp.awarded > 0 ? 'bg-emerald-50/50 border-emerald-200' : 'bg-slate-50 border-slate-200'}`}>
                    <div className="flex gap-4">
                      <div className="mt-1">
                        {vp.awarded > 0 ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <XCircle className="w-5 h-5 text-slate-300" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-bold text-slate-900 text-sm">Criterion {vp.id}</p>
                            <p className="text-xs text-slate-700 mt-1">{vp.text}</p>
                          </div>
                          <div className="font-black text-sm whitespace-nowrap ml-4">
                            {vp.awarded} mark
                          </div>
                        </div>

                        {vp.awarded > 0 && vp.evidence_text ? (
                          <div className="mt-3 p-3 bg-white border border-emerald-100 rounded-xl">
                            <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-1 flex items-center gap-1">
                              <Hash className="w-3 h-3" /> Extracted Evidence 
                              <span className="text-emerald-400 font-medium ml-2">[{vp.evidence_span?.start} - {vp.evidence_span?.end}]</span>
                            </p>
                            <p className="text-xs font-medium text-slate-800 italic">"{vp.evidence_text}"</p>
                          </div>
                        ) : (
                          <div className="mt-3 p-3 bg-white border border-slate-100 rounded-xl">
                            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1 flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" /> Not Awarded
                            </p>
                            <p className="text-xs font-medium text-slate-500">{vp.reason}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      
      {/* Provenance footer */}
      <div className="text-center text-xs font-medium text-slate-400 pt-8 pb-4">
        <p>Engine: {provenance?.scorer} • Matcher: {provenance?.matcher} • Model: {provenance?.model_id}</p>
      </div>

    </div>
  );
}

export default function ResultsView() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-slate-500">Loading results...</div>}>
      <ResultsContent />
    </Suspense>
  );
}
