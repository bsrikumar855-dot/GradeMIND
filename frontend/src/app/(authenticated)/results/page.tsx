'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { 
  PieChart, Pie, Cell, 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
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
  ChevronRight
} from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';

const normalizeList = (value: any): string[] => {
  if (Array.isArray(value)) return value.map(item => String(item).trim()).filter(Boolean);
  if (!value) return [];
  return String(value)
    .split('.')
    .map(item => item.trim())
    .filter(Boolean);
};

const formatListText = (items: string[], emptyText: string) => {
  if (!items.length) return emptyText;
  return items.map(item => item.endsWith('.') ? item : `${item}.`).join(' ');
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

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError('');
        setReport(null);
        setSubmission(null);

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
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20"></div>
          <div className="absolute inset-0 rounded-full border-4 border-emerald-500 border-t-transparent animate-spin"></div>
        </div>
        <p className="text-slate-500 font-bold text-sm animate-pulse">Compiling 120B Evaluation Reports & Annotated PDF...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-8 max-w-3xl mx-auto space-y-6 text-center">
        <div className="glass-card p-12 rounded-3xl border border-slate-200 flex flex-col items-center gap-6">
          <div className="w-16 h-16 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-slate-900 mb-2">No Evaluated Report Found</h1>
            <p className="text-slate-500 text-sm max-w-md mx-auto">{error || 'Unable to display evaluation metrics for this student.'}</p>
          </div>
          <div className="flex gap-4">
            <button 
              onClick={() => router.push('/upload')}
              className="px-6 py-3 bg-slate-900 text-white font-bold text-xs rounded-xl shadow-lg shadow-slate-900/20"
            >
              Upload New Sheet
            </button>
            <button 
              onClick={() => router.push('/dashboard')}
              className="px-6 py-3 bg-slate-100 text-slate-700 font-bold text-xs rounded-xl border border-slate-200"
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

  const getGrade = (pct: number) => {
    if (pct >= 90) return 'A+';
    if (pct >= 80) return 'A';
    if (pct >= 70) return 'B';
    if (pct >= 60) return 'C';
    if (pct >= 50) return 'D';
    return 'F';
  };
  const grade = getGrade(percentage);

  let correctCount = 0;
  let partialCount = 0;
  let incorrectCount = 0;

  const barData = questions.map((q: any) => {
    const score = q.score_awarded ?? 0;
    const max = q.max_marks ?? 1;
    if (score === max) correctCount++;
    else if (score > 0) partialCount++;
    else incorrectCount++;
    return {
      question: `Q${q.question_number}`,
      marks: score,
      max: max
    };
  });

  const pieData = [
    { name: 'Full Marks', value: correctCount || (percentage > 50 ? 1 : 0), color: '#10B981' },
    { name: 'Partial Credit', value: partialCount, color: '#3B82F6' },
    { name: 'Needs Review', value: incorrectCount, color: '#EF4444' },
  ].filter(item => item.value > 0);

  const strengths = normalizeList(evalSummary.strengths);
  const weaknesses = normalizeList(evalSummary.weaknesses);
  const improvements = normalizeList(evalSummary.improvements);

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
    } else {
      alert('Submission ID is not available.');
    }
  };

  const getInlinePdfUrl = () => {
    if (!selectedSubmissionId) return '';
    const tokenCookie = document.cookie
      .split('; ')
      .find(row => row.startsWith('grademind_auth='));
    const token = tokenCookie ? tokenCookie.split('=')[1] : '';
    return `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/submissions/${selectedSubmissionId}/pdf?inline=true&token=${token}`;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-16">
      
      {/* Header Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.back()}
            className="p-2.5 bg-white hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors text-slate-700 shadow-sm"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Evaluation Report Breakdown</h1>
            <p className="text-xs text-slate-400">Groq 120B AI Scorecard & Annotated Answer Script</p>
          </div>
        </div>

        <button 
          onClick={handleDownloadPDF}
          className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-lg shadow-slate-900/20 flex items-center gap-2 transition-all"
        >
          <Download className="w-4 h-4" /> Download PDF Report
        </button>
      </div>

      {/* 1. Student Summary Glass Banner */}
      <div className="glass-card rounded-3xl p-8 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white shadow-2xl border border-slate-700/50 flex flex-col lg:flex-row justify-between items-center gap-8">
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 rounded-2xl flex items-center justify-center font-black text-2xl shadow-xl shadow-emerald-500/20">
            {metadata.student_name ? metadata.student_name.split(' ').map((n: string) => n[0]).join('').substring(0, 2).toUpperCase() : 'ST'}
          </div>
          <div>
            <h2 className="text-3xl font-black tracking-tight text-white">{metadata.student_name || submission?.student_name}</h2>
            <p className="text-slate-300 font-semibold text-xs mt-1">Roll Number: {metadata.student_roll_number || submission?.student_roll_number}</p>
            <div className="flex items-center gap-2 mt-3">
              <span className="text-[10px] font-bold px-3 py-1 bg-white/10 text-slate-300 rounded-full border border-white/15">
                Exam ID: {metadata.exam_id?.substring(0, 8) || 'N/A'}
              </span>
              <span className="text-[10px] font-bold px-3 py-1 bg-emerald-500/20 text-emerald-400 rounded-full border border-emerald-500/30 flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Groq 120B Evaluated
              </span>
            </div>
          </div>
        </div>

        {/* Metrics Pill Grid */}
        <div className="flex flex-wrap sm:flex-nowrap gap-4 w-full lg:w-auto">
          <div className="bg-white/10 border border-white/15 px-6 py-4 rounded-2xl backdrop-blur-md flex-1 sm:flex-none min-w-[130px]">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Total Marks</p>
            <p className="text-2xl font-black text-white">{totalScore} <span className="text-xs text-slate-400 font-medium">/ {maxScore}</span></p>
          </div>

          <div className="bg-white/10 border border-white/15 px-6 py-4 rounded-2xl backdrop-blur-md flex-1 sm:flex-none min-w-[130px]">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Percentage</p>
            <p className="text-2xl font-black text-emerald-400">{percentage}%</p>
          </div>

          <div className="bg-gradient-to-tr from-emerald-600 to-teal-500 px-8 py-4 rounded-2xl shadow-xl shadow-emerald-500/25 flex-1 sm:flex-none flex items-center justify-between gap-6 min-w-[140px]">
            <div>
              <p className="text-xs font-bold text-slate-950/80 uppercase tracking-wider mb-1">Grade</p>
              <p className="text-4xl font-black text-slate-950">{grade}</p>
            </div>
            <Award className="w-10 h-10 text-slate-950/40" />
          </div>
        </div>
      </div>

      {/* 2. Charts & AI Insights Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left 2 Cols: Question vs Marks Chart & Distribution */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Bar Chart */}
          <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Question-wise Marks Distribution</h3>
                <p className="text-xs text-slate-400">Score awarded per question against maximum allocated marks</p>
              </div>
            </div>

            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                  <XAxis dataKey="question" axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 12, fontWeight: 700 }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748B', fontSize: 12, fontWeight: 700 }} />
                  <Tooltip 
                    cursor={{ fill: '#F1F5F9' }}
                    contentStyle={{ borderRadius: '16px', border: '1px solid #E2E8F0', boxShadow: '0 10px 30px rgba(0,0,0,0.08)' }}
                  />
                  <Bar dataKey="marks" fill="#10B981" radius={[8, 8, 0, 0]} maxBarSize={45} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Performance Profile */}
          <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6">
            <h3 className="text-lg font-bold text-slate-900">Performance Profile</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="p-5 rounded-2xl bg-emerald-50/60 border border-emerald-200/80 space-y-3">
                <div className="flex items-center gap-2 text-emerald-800 font-bold text-sm">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Strengths Identified
                </div>
                <div className="space-y-1.5 text-xs text-emerald-900 font-medium">
                  {strengths.length > 0 ? strengths.map((st, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-emerald-500 font-bold">•</span>
                      <span>{st}</span>
                    </div>
                  )) : <p className="text-slate-400">Response shows basic subject alignment.</p>}
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-amber-50/60 border border-amber-200/80 space-y-3">
                <div className="flex items-center gap-2 text-amber-800 font-bold text-sm">
                  <Target className="w-4 h-4 text-amber-600" /> Key Areas for Improvement
                </div>
                <div className="space-y-1.5 text-xs text-amber-900 font-medium">
                  {weaknesses.length > 0 ? weaknesses.map((wk, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-amber-500 font-bold">•</span>
                      <span>{wk}</span>
                    </div>
                  )) : <p className="text-slate-400">No major missing concepts detected.</p>}
                </div>
              </div>
            </div>
          </div>

        </div>

        {/* Right Col: AI Insights */}
        <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6 flex flex-col justify-between">
          <div className="space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-purple-500/10 text-purple-600 rounded-2xl">
                <Brain className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">AI Examiner Insights</h3>
                <p className="text-xs text-slate-400">Groq 120B LLM Evaluation</p>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
              <h4 className="text-xs font-bold text-slate-900 flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-amber-500" /> Evaluator Summary
              </h4>
              <p className="text-xs text-slate-600 leading-relaxed font-medium">
                {evalSummary.summary || 'Student response was evaluated using 120B parameter academic criteria.'}
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-emerald-50/60 border border-emerald-200/80 space-y-2">
              <h4 className="text-xs font-bold text-emerald-950 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-emerald-600" /> Recommended Action
              </h4>
              <p className="text-xs text-emerald-900 leading-relaxed font-medium">
                {formatListText(improvements, 'Review missing key concepts in textbook and re-examine question breakdown.')}
              </p>
            </div>
          </div>

          <button 
            onClick={handleDownloadPDF}
            className="w-full py-3.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-lg shadow-slate-900/20 flex items-center justify-center gap-2 transition-all mt-6"
          >
            <Download className="w-4 h-4" /> Download Official PDF Report
          </button>
        </div>

      </div>

      {/* Embedded Annotated Answer Sheet Viewer */}
      <div className="glass-card rounded-3xl overflow-hidden shadow-2xl flex flex-col h-[850px]">
        <div className="p-5 border-b border-slate-200 bg-slate-900 text-white flex items-center justify-between">
          <h3 className="text-base font-bold flex items-center gap-2.5">
            <FileText className="w-5 h-5 text-emerald-400" />
            Annotated Answer Sheet Scan & AI Markings
          </h3>
          <button 
            onClick={handleDownloadPDF}
            className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" /> Download File
          </button>
        </div>
        <iframe 
          src={getInlinePdfUrl()} 
          className="w-full flex-1 border-0 bg-slate-100" 
          title="Annotated Report PDF"
        />
      </div>

      {/* Question breakdown table */}
      <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6">
        <h3 className="text-lg font-bold text-slate-900">Question Breakdown Table</h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="pb-3">Question</th>
                <th className="pb-3">Score</th>
                <th className="pb-3">Matched Concepts</th>
                <th className="pb-3">Missing Concepts</th>
                <th className="pb-3">AI Feedback</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {questions.map((row: any, idx: number) => {
                const score = row.score_awarded ?? 0;
                const max = row.max_marks ?? 1;
                const isFull = score === max;

                return (
                  <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-4 font-bold text-slate-900">
                      Question #{row.question_number}
                    </td>
                    <td className="py-4">
                      <span className={`px-2.5 py-1 rounded-full font-black text-xs ${
                        isFull ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20' : 'bg-slate-100 text-slate-700'
                      }`}>
                        {score} / {max}
                      </span>
                    </td>
                    <td className="py-4">
                      <div className="flex flex-wrap gap-1">
                        {row.matched_keywords && row.matched_keywords.length > 0 ? (
                          row.matched_keywords.map((kw: string, i: number) => (
                            <span key={i} className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold text-[10px]">
                              {kw}
                            </span>
                          ))
                        ) : <span className="text-slate-400">None</span>}
                      </div>
                    </td>
                    <td className="py-4">
                      <div className="flex flex-wrap gap-1">
                        {row.missing_concepts && row.missing_concepts.length > 0 ? (
                          row.missing_concepts.map((mc: string, i: number) => (
                            <span key={i} className="px-2 py-0.5 rounded bg-amber-50 text-amber-700 font-semibold text-[10px]">
                              {mc}
                            </span>
                          ))
                        ) : <span className="text-slate-400">None</span>}
                      </div>
                    </td>
                    <td className="py-4 text-slate-600 font-medium max-w-xs leading-relaxed">
                      {row.criteria_feedback || 'Graded accurately against rubric.'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <ResultsContent />
    </Suspense>
  );
}
