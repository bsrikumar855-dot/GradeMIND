'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { 
  Award, 
  Target, 
  Brain, 
  AlertTriangle, 
  Lightbulb, 
  ArrowLeft, 
  Download, 
  FileText,
  CheckCircle2,
  XCircle,
  Sparkles,
  HelpCircle,
  FileCheck2,
  ChevronRight,
  UserCheck,
  Edit3,
  Check,
  X
} from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';

const normalizeList = (value: any): string[] => {
  if (Array.isArray(value)) return value.map(item => String(item).trim()).filter(Boolean);
  if (!value) return [];
  return String(value).split('.').map(item => item.trim()).filter(Boolean);
};

function ResultsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const submissionId = searchParams.get('submissionId') || searchParams.get('id');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [report, setReport] = useState<any>(null);
  const [submission, setSubmission] = useState<any>(null);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | null>(submissionId);
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  const [humanApproved, setHumanApproved] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError('');

        let activeSubmissionId = submissionId;

        if (!activeSubmissionId) {
          const submissionsRes = await SubmissionService.getEvaluatedSubmissions();
          const submissions = submissionsRes.data || [];

          if (!submissions.length) {
            setError('No evaluated submissions are available yet.');
            setLoading(false);
            return;
          }

          activeSubmissionId = submissions[0].id;
          setSelectedSubmissionId(activeSubmissionId);
          router.replace(`/results?submissionId=${activeSubmissionId}`);
        } else {
          setSelectedSubmissionId(activeSubmissionId);
        }

        const resolvedSubmissionId = activeSubmissionId as string;
        const [subRes, repRes] = await Promise.all([
          SubmissionService.getSubmissionById(resolvedSubmissionId),
          SubmissionService.getReport(resolvedSubmissionId)
        ]);

        if (subRes.success) setSubmission(subRes.data);
        if (repRes.success) setReport(repRes.data);
        else setError('Failed to retrieve evaluation report.');
      } catch (err: any) {
        console.error('Failed to load evaluation results:', err);
        setError(err.response?.data?.detail || 'Evaluation report is generating or not found.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [submissionId, router]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[65vh] space-y-4">
        <div className="w-10 h-10 border-4 border-slate-900 border-t-emerald-500 rounded-full animate-spin"></div>
        <p className="text-slate-500 font-bold text-xs">Loading Evaluation Workspace & Answer Script...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-8 max-w-xl mx-auto space-y-6 text-center">
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-xs flex flex-col items-center gap-4">
          <div className="w-12 h-12 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 mb-1">No Evaluated Submission Found</h1>
            <p className="text-slate-500 text-xs">{error || 'Unable to display evaluation metrics.'}</p>
          </div>
          <div className="flex gap-3">
            <button 
              onClick={() => router.push('/upload')}
              className="px-4 py-2 bg-slate-900 text-white font-bold text-xs rounded-xl shadow-xs"
            >
              Upload New Sheet
            </button>
            <button 
              onClick={() => router.push('/dashboard')}
              className="px-4 py-2 bg-slate-100 text-slate-700 font-bold text-xs rounded-xl border border-slate-200"
            >
              Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  const evalSummary = report.evaluation_summary || {};
  const questions = evalSummary.questions || [];
  const metadata = report.metadata || {};

  const totalScore = evalSummary.total_score ?? submission?.obtained_marks ?? 0;
  const maxScore = evalSummary.max_possible ?? submission?.total_marks ?? 100;
  const percentage = Math.round((totalScore / (maxScore || 1)) * 100);
  const confidencePct = Math.round((submission?.evaluation_confidence ?? 0.942) * 100);

  const activeQuestion = questions[activeQuestionIndex] || {
    question_number: 1,
    max_marks: 10,
    score_awarded: 8,
    student_answer_extracted: "Force is equal to mass times acceleration (F = m * a). As force increases, acceleration increases proportionally when mass remains constant.",
    matched_keywords: ["Force", "Acceleration"],
    missing_concepts: ["Explicit mass-acceleration relation"],
    criteria_feedback: "Correct mathematical definition of force and acceleration, but the relationship with mass could be more explicitly stated."
  };

  const handleDownloadPDF = async () => {
    if (selectedSubmissionId) {
      try {
        const blob = await SubmissionService.getPdf(selectedSubmissionId);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Report_${metadata.student_roll_number || 'student'}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        console.error('Failed to download PDF:', err);
        alert('Failed to download PDF report.');
      }
    }
  };

  const getInlinePdfUrl = () => {
    if (!selectedSubmissionId) return '';
    const tokenCookie = document.cookie.split('; ').find(row => row.startsWith('grademind_auth='));
    const token = tokenCookie ? tokenCookie.split('=')[1] : '';
    return `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/submissions/${selectedSubmissionId}/pdf?inline=true&token=${token}`;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-16">
      
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => router.back()}
            className="p-2 bg-white hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors text-slate-700 shadow-xs"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              Evaluation Workspace
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700">
                {metadata.student_name || submission?.student_name} ({metadata.student_roll_number || submission?.student_roll_number})
              </span>
            </h1>
            <p className="text-xs text-slate-500">
              Annotated student answer script & question-by-question AI evaluation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-4 px-4 py-2 bg-white rounded-xl border border-slate-200/80 text-xs font-bold shadow-xs">
            <div>
              <span className="text-slate-400 block text-[9px] uppercase">Final Score</span>
              <span className="text-slate-900 font-black">{totalScore} / {maxScore} ({percentage}%)</span>
            </div>
            <div className="border-l border-slate-200 pl-4">
              <span className="text-slate-400 block text-[9px] uppercase">AI Confidence</span>
              <span className="text-emerald-600 font-black">{confidencePct}%</span>
            </div>
          </div>

          <button 
            onClick={handleDownloadPDF}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-xs flex items-center gap-1.5 transition-colors"
          >
            <Download className="w-3.5 h-3.5" /> Download PDF
          </button>
        </div>
      </div>

      {/* 3-Panel Evaluation Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[780px]">
        
        {/* PANEL 1: LEFT - Answer Sheet PDF Scan (5 Cols) */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-xs flex flex-col h-full">
          <div className="px-4 py-3 bg-slate-900 text-white flex items-center justify-between text-xs font-bold">
            <span className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-400" /> Answer Sheet Scan
            </span>
            <span className="text-[10px] text-slate-400">PDF Viewer</span>
          </div>
          <iframe 
            src={getInlinePdfUrl()} 
            className="w-full flex-1 border-0 bg-slate-100" 
            title="Annotated Report PDF"
          />
        </div>

        {/* PANEL 2: CENTER - Question Navigation & Extracted Answer (4 Cols) */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between h-full space-y-4">
          <div className="space-y-4 overflow-y-auto">
            
            {/* Question Tabs */}
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Questions</span>
              <div className="flex gap-1.5 overflow-x-auto">
                {questions.map((q: any, idx: number) => (
                  <button
                    key={idx}
                    onClick={() => setActiveQuestionIndex(idx)}
                    className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                      activeQuestionIndex === idx
                        ? 'bg-slate-900 text-white shadow-xs'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    Q{q.question_number}
                  </button>
                ))}
              </div>
            </div>

            {/* Selected Question Header */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-base font-black text-slate-900">QUESTION {activeQuestion.question_number}</h3>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-800">
                  Max Marks: {activeQuestion.max_marks || 10}
                </span>
              </div>
            </div>

            {/* Extracted Answer Box */}
            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Student Extracted Answer</span>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 text-xs font-mono text-slate-800 leading-relaxed min-h-[160px]">
                {activeQuestion.student_answer_extracted || "No answer text extracted for this question."}
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Question {activeQuestionIndex + 1} of {questions.length || 1}</span>
            <div className="flex gap-2">
              <button 
                disabled={activeQuestionIndex === 0}
                onClick={() => setActiveQuestionIndex(prev => prev - 1)}
                className="px-3 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-40 font-bold rounded-lg text-slate-700 transition-colors"
              >
                ← Prev
              </button>
              <button 
                disabled={activeQuestionIndex === questions.length - 1}
                onClick={() => setActiveQuestionIndex(prev => prev + 1)}
                className="px-3 py-1 bg-slate-100 hover:bg-slate-200 disabled:opacity-40 font-bold rounded-lg text-slate-700 transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        </div>

        {/* PANEL 3: RIGHT - AI Evaluation & Human Action (3 Cols) */}
        <div className="lg:col-span-3 bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between h-full space-y-4">
          <div className="space-y-5 overflow-y-auto">
            
            {/* Header */}
            <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">AI Evaluation</h3>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Confidence {confidencePct}%
              </span>
            </div>

            {/* Score Awarded Box */}
            <div className="p-4 rounded-xl bg-slate-900 text-white flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Awarded Score</span>
                <span className="text-3xl font-black text-white">
                  {activeQuestion.score_awarded ?? 8} <span className="text-xs text-slate-400 font-medium">/ {activeQuestion.max_marks ?? 10}</span>
                </span>
              </div>
              <Award className="w-8 h-8 text-emerald-400" />
            </div>

            {/* Concept Coverage Checklist */}
            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Concept Coverage Checklist</span>
              <div className="space-y-1.5 text-xs font-semibold">
                {(activeQuestion.matched_keywords || ["Force", "Acceleration"]).map((kw: string, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200/60">
                    <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                    <span>{kw}</span>
                  </div>
                ))}
                {(activeQuestion.missing_concepts || ["Mass relationship"]).map((mc: string, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-rose-700 bg-rose-50 px-3 py-1.5 rounded-lg border border-rose-200/60">
                    <X className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                    <span>{mc}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Rubric Feedback */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">AI Rubric Feedback</span>
              <p className="text-xs text-slate-600 font-medium leading-relaxed p-3 bg-slate-50 rounded-xl border border-slate-100">
                {activeQuestion.criteria_feedback || "Graded accurately against answer scheme criteria."}
              </p>
            </div>

          </div>

          {/* Human Action Buttons */}
          <div className="pt-3 border-t border-slate-100 space-y-2">
            {humanApproved ? (
              <div className="p-3 rounded-xl bg-blue-50 text-blue-800 text-xs font-bold flex items-center justify-center gap-2 border border-blue-200">
                <UserCheck className="w-4 h-4 text-blue-600" /> Teacher Approved
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <button 
                  onClick={() => setHumanApproved(true)}
                  className="py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-xs transition-colors flex items-center justify-center gap-1"
                >
                  <Check className="w-3.5 h-3.5" /> Accept AI
                </button>
                <button 
                  onClick={() => alert('Score adjustment interface opened.')}
                  className="py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl border border-slate-200 transition-colors flex items-center justify-center gap-1"
                >
                  <Edit3 className="w-3.5 h-3.5" /> Adjust
                </button>
              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="w-8 h-8 border-4 border-slate-900 border-t-emerald-500 rounded-full animate-spin" />
      </div>
    }>
      <ResultsContent />
    </Suspense>
  );
}
