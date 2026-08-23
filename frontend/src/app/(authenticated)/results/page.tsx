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
  Hash,
  Download,
  FileText
} from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';

function ResultsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlJobId = searchParams.get('job_id');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [jobData, setJobData] = useState<any>(null);
  const [annotatedPdfUrl, setAnnotatedPdfUrl] = useState<string | null>(null);
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [activeJobId, setActiveJobId] = useState<string>(urlJobId || '');

  // 1. Fetch available evaluated submissions list
  useEffect(() => {
    async function loadSubmissionsList() {
      try {
        const res = await SubmissionService.getEvaluatedSubmissions();
        const list = res.data || [];
        setSubmissions(list);
        if (!urlJobId && list.length > 0) {
          setActiveJobId(list[0].id);
        }
      } catch (err) {
        console.warn('Failed to fetch submissions list:', err);
      }
    }
    loadSubmissionsList();
  }, [urlJobId]);

  // 2. Poll & fetch active job data
  useEffect(() => {
    const currentId = urlJobId || activeJobId;
    if (!currentId) {
      setLoading(false);
      return;
    }

    let interval: any = null;

    async function checkJob() {
      try {
        const res = await SubmissionService.pollGradeJob(currentId);
        const reportObj = res.report || (res.questions || res.totals ? res : null);
        const isDone = res.status === 'completed' || res.status === 'COMPLETE' || (res.state && res.state.status === 'COMPLETE') || !!reportObj;

        if (isDone) {
          if (reportObj) {
            setJobData(reportObj);
            setError('');
          }
          if (res.annotated_pdf_url) {
            const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            setAnnotatedPdfUrl(`${base}${res.annotated_pdf_url}`);
          }
          setLoading(false);
          if (interval) clearInterval(interval);
        } else if (res.status === 'failed' || res.status === 'FAILED') {
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

    setLoading(true);
    checkJob();
    interval = setInterval(checkJob, 2000);

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [urlJobId, activeJobId]);

  if (loading && !jobData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[65vh] space-y-4">
        <div className="w-10 h-10 border-4 border-slate-900 border-t-emerald-500 rounded-full animate-spin"></div>
        <p className="text-slate-500 font-bold text-xs">Waiting for AI Pipeline to complete...</p>
      </div>
    );
  }

  if (error || !jobData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <AlertTriangle className="w-12 h-12 text-rose-500 mb-2" />
        <h2 className="text-lg font-bold text-slate-900">Oops! Something went wrong</h2>
        <p className="text-slate-500 text-sm mt-1">{error || 'Job data not found.'}</p>
        
        {submissions.length > 0 && (
          <div className="w-72 mt-4">
            <p className="text-xs font-bold text-slate-600 mb-2 text-center">Select another evaluated script:</p>
            <select
              value={activeJobId || ''}
              onChange={(e) => {
                const val = e.target.value;
                setActiveJobId(val);
                router.replace(`/results?job_id=${val}`);
              }}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 bg-white text-slate-900 font-bold text-xs shadow-sm focus:outline-none cursor-pointer"
            >
              {submissions.map((sub: any) => (
                <option key={sub.id} value={sub.id}>
                  {sub.student_name} ({sub.student_roll_number})
                </option>
              ))}
            </select>
          </div>
        )}

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
  const scoredQs = questions?.filter((q: any) => q.status === 'scored') || [];
  const routedQs = questions?.filter((q: any) => q.status === 'routed') || [];
  const noSchemeQs = questions?.filter((q: any) => q.status.includes('no scheme')) || [];

  return (
    <div className="flex-1 flex flex-col space-y-5 text-left w-full">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-200 pb-5">
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
            <p className="text-slate-500 text-xs font-semibold mt-0.5">
              Job ID: {activeJobId || urlJobId}
            </p>
          </div>
        </div>

        {submissions.length > 0 && (
          <div className="w-full md:w-80">
            <select
              value={activeJobId || urlJobId || ''}
              onChange={(e) => {
                const val = e.target.value;
                setActiveJobId(val);
                router.replace(`/results?job_id=${val}`);
              }}
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 bg-white text-slate-900 font-bold text-xs shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer"
            >
              {submissions.map((sub: any) => (
                <option key={sub.id} value={sub.id}>
                  {sub.student_name} ({sub.student_roll_number})
                </option>
              ))}
            </select>
          </div>
        )}
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
        <details open className="bg-amber-50 border border-amber-200 rounded-3xl p-6 group [&_summary::-webkit-details-marker]:hidden">
          <summary className="text-sm font-black text-amber-900 uppercase tracking-widest flex items-center justify-between cursor-pointer list-none">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> What this run could not do
            </div>
            <div className="transform transition-transform group-open:rotate-180">
              ▼
            </div>
          </summary>
          <div className="space-y-4 mt-4">
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
        </details>
      )}

      {/* Annotated PDF Preview & Download */}
      {annotatedPdfUrl && (
        <div className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileCheck2 className="w-5 h-5 text-emerald-500" />
              <h3 className="text-lg font-black text-slate-900">Annotated Answer Script</h3>
            </div>
            <div className="flex items-center gap-3">
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v2/grade/${activeJobId || urlJobId}/student-report?format=html`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-2.5 bg-[#183B25] hover:bg-[#122c1b] text-white font-bold text-xs rounded-xl transition-all shadow-md flex items-center gap-2 border border-emerald-500/40"
              >
                <FileText className="w-4 h-4 text-emerald-300" />
                Student Diagnostic Report (HTML)
              </a>
              <a
                href={annotatedPdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs rounded-xl transition-all shadow-lg shadow-emerald-500/25 flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download Annotated Script
              </a>
            </div>
          </div>
          <div className="p-4">
            <iframe
              src={`${annotatedPdfUrl}#page=1`}
              className="w-full rounded-2xl border border-slate-200"
              style={{ height: '600px' }}
              title="Annotated answer script preview"
            />
          </div>
        </div>
      )}

      {/* Questions List */}
      <div className="space-y-8">
        
        {/* Scored Questions */}
        {scoredQs.length > 0 && (
          <div className="space-y-6">
            <h3 className="text-lg font-black text-slate-900">Scored Questions</h3>
            {scoredQs.map((q: any, i: number) => (
              <div key={i} className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-sm">
                <div className="p-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-slate-200 text-slate-700 flex items-center justify-center font-black tabular-nums">
                      Q{q.question_number}
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" /> SCORED
                      </h4>
                      {q.flagged && (
                        <p className="text-xs font-bold text-rose-600 mt-0.5">FLAGGED by safety boundaries</p>
                      )}
                    </div>
                  </div>
                  <div className="text-right tabular-nums">
                    <p className="text-xl font-black text-slate-900">{q.mark} <span className="text-sm text-slate-400">/ {q.max_marks}</span></p>
                  </div>
                </div>

                {q.value_points && q.value_points.length > 0 && (
                  <div className="p-5 space-y-4">
                    {q.value_points.map((vp: any, vpIdx: number) => (
                      <div key={vpIdx} className={`p-4 rounded-2xl border ${vp.awarded > 0 ? 'bg-emerald-50/50 border-emerald-200' : 'bg-slate-50 border-slate-200 opacity-60 hover:opacity-100 transition-opacity'}`}>
                        <div className="flex gap-4">
                          <div className="mt-1">
                            {vp.awarded > 0 ? (
                              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                            ) : (
                              <XCircle className="w-5 h-5 text-slate-400" />
                            )}
                          </div>
                          <div className="flex-1 overflow-hidden">
                            <div className="flex items-start justify-between gap-4">
                              <div>
                                <p className="font-bold text-slate-900 text-sm tabular-nums">Criterion {vp.id}</p>
                                <p className="text-xs text-slate-700 mt-1">{vp.text}</p>
                              </div>
                              <div className="font-black text-sm whitespace-nowrap tabular-nums">
                                {vp.awarded} mark
                              </div>
                            </div>

                            {vp.awarded > 0 ? (
                              <div className="mt-3 p-3.5 bg-emerald-50/80 border border-emerald-200/80 rounded-xl space-y-2">
                                <div className="flex items-center justify-between gap-2">
                                  <p className="text-[10px] font-black text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Awarded ({vp.awarded} {vp.awarded === 1 ? 'mark' : 'marks'})
                                  </p>
                                  {vp.reason && (
                                    <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100/90 px-2 py-0.5 rounded border border-emerald-300/60 font-mono">
                                      {vp.reason}
                                    </span>
                                  )}
                                </div>
                                {vp.evidence_text && (
                                  <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                                    <p className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest mb-1.5 flex items-center gap-1">
                                      <Hash className="w-3 h-3 text-emerald-400" /> Extracted Evidence 
                                      {vp.evidence_span && (
                                        <span className="text-emerald-200/60 font-medium ml-1.5 font-mono text-[10px]">
                                          [{vp.evidence_span.start} - {vp.evidence_span.end}]
                                        </span>
                                      )}
                                    </p>
                                    <p className="text-xs font-medium text-emerald-50 font-mono leading-relaxed whitespace-pre-wrap break-words">&quot;{vp.evidence_text}&quot;</p>
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div className="mt-3 p-3 bg-white border border-slate-200 rounded-xl">
                                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1 flex items-center gap-1">
                                  <AlertTriangle className="w-3 h-3 text-amber-500" /> Not Awarded (0 marks)
                                </p>
                                <p className="text-xs font-medium text-slate-600 font-mono">{vp.reason}</p>
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
        )}

        {/* Routed Questions */}
        {routedQs.length > 0 && (
          <details className="bg-white rounded-3xl border border-slate-200 shadow-sm group [&_summary::-webkit-details-marker]:hidden">
            <summary className="p-5 flex items-center justify-between cursor-pointer list-none">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-black text-slate-900 tabular-nums">{routedQs.length} questions sent to a human</h3>
              </div>
              <div className="text-slate-400 transform transition-transform group-open:rotate-180">
                ▼
              </div>
            </summary>
            <div className="p-5 border-t border-slate-100 space-y-4">
              {routedQs.map((q: any, i: number) => (
                <div key={i} className="flex items-start gap-4 p-4 rounded-2xl bg-amber-50/50 border border-amber-100">
                  <div className="w-10 h-10 shrink-0 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center font-black tabular-nums">
                    Q{q.question_number}
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900 text-sm">ROUTED</h4>
                    <p className="text-xs font-bold text-amber-700 mt-1">Reason: {q.routing_reason}</p>
                  </div>
                </div>
              ))}
            </div>
          </details>
        )}

        {/* No Scheme Questions */}
        {noSchemeQs.length > 0 && (
          <div className="bg-slate-50 rounded-2xl border border-slate-200 p-4">
            <div className="flex items-center gap-3">
              <HelpCircle className="w-5 h-5 text-slate-400" />
              <p className="text-sm font-bold text-slate-600">
                <span className="text-slate-900 tabular-nums">{noSchemeQs.length} questions</span> skipped because no marking scheme was provided.
              </p>
            </div>
          </div>
        )}

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
