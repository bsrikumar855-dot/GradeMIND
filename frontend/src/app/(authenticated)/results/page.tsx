'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { 
  PieChart, Pie, Cell, 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
import { Award, Target, Brain, AlertTriangle, Lightbulb, ArrowLeft, Download, FileText } from 'lucide-react';
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

const splitFeedbackItem = (value: string) => {
  const parts = String(value || '').split(':');
  return {
    title: parts.length > 1 ? parts[0].trim() : '',
    desc: (parts.length > 1 ? parts.slice(1).join(':') : parts[0]).trim(),
  };
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
        console.log("submissionId", activeSubmissionId);

        if (!activeSubmissionId) {
          const submissionsRes = await SubmissionService.getEvaluatedSubmissions();
          const submissions = submissionsRes.data || [];
          console.log("evaluated submissions", submissions);

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

        // Fetch submission details and report
        const [subRes, repRes] = await Promise.all([
          SubmissionService.getSubmissionById(resolvedSubmissionId),
          SubmissionService.getReport(resolvedSubmissionId)
        ]);

        if (subRes.success) {
          setSubmission(subRes.data);
        }

        if (repRes.success) {
          setReport(repRes.data);
        } else {
          setError('Failed to retrieve evaluation report.');
        }
      } catch (err: any) {
        console.error('Failed to load evaluation results:', err);
        setError(err.response?.data?.detail || 'Evaluation report is still generating or not found.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [submissionId, router]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-brand-primary border-t-transparent"></div>
        <p className="text-gray-500 font-semibold">Analyzing evaluation reports...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-8 max-w-4xl mx-auto space-y-6 text-center">
        <div className="bg-white p-12 rounded-3xl border border-gray-100 shadow-sm flex flex-col items-center gap-6">
          <div className="w-16 h-16 bg-red-50 text-red-500 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-brand-dark mb-2">No Evaluated Reports Yet</h1>
            <p className="text-gray-500 max-w-md mx-auto">{error || 'Unable to display the evaluation metrics for this student.'}</p>
          </div>
          <div className="flex gap-4">
            <button 
              onClick={() => router.push('/reports')}
              className="px-6 py-3 bg-brand-primary text-white font-bold rounded-xl shadow-md"
            >
              Go to Reports Center
            </button>
            <button 
              onClick={() => router.push('/dashboard')}
              className="px-6 py-3 bg-gray-100 text-brand-dark font-bold rounded-xl border border-gray-200"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  const evalSummary = report.evaluation_summary || {};
  const questions = evalSummary.questions || [];
  const metadata = report.metadata || {};

  // Score details
  const totalScore = evalSummary.total_score ?? submission?.obtained_marks ?? 0;
  const maxScore = evalSummary.max_possible ?? submission?.total_marks ?? 100;
  const percentage = Math.round((totalScore / (maxScore || 1)) * 100);

  // Grade helper
  const getGrade = (pct: number) => {
    if (pct >= 90) return 'A+';
    if (pct >= 80) return 'A';
    if (pct >= 70) return 'B';
    if (pct >= 60) return 'C';
    if (pct >= 50) return 'D';
    return 'F';
  };
  const grade = getGrade(percentage);

  // Parse questions for correctness charts
  let correctCount = 0;
  let partialCount = 0;
  let incorrectCount = 0;

  const barData = questions.map((q: any) => {
    const score = q.score_awarded ?? 0;
    const max = q.max_marks ?? 1;
    if (score === max) {
      correctCount++;
    } else if (score > 0) {
      partialCount++;
    } else {
      incorrectCount++;
    }
    return {
      question: `Q${q.question_number}`,
      marks: score,
      max: max
    };
  });

  const pieData = [
    { name: 'Correct', value: correctCount || 1, color: '#86B77B' },
    { name: 'Partial', value: partialCount, color: '#5B8DEF' },
    { name: 'Incorrect', value: incorrectCount, color: '#F87171' },
  ].filter(item => item.value > 0);

  // Strengths / Weaknesses list
  const strengths = normalizeList(evalSummary.strengths);
  const weaknesses = normalizeList(evalSummary.weaknesses);
  const improvements = normalizeList(evalSummary.improvements);
  const recommendations = normalizeList(evalSummary.recommendations || evalSummary.study_recommendations);

  const handleDownloadPDF = () => {
    if (selectedSubmissionId) {
      // Create a direct API download url
      const tokenCookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('grademind_auth='));
      const token = tokenCookie ? tokenCookie.split('=')[1] : '';
      
      const downloadUrl = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/submissions/${selectedSubmissionId}/pdf?token=${token}`;
      window.open(downloadUrl, '_blank');
    } else {
      alert('Submission ID is not available.');
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Navigation Header */}
      <div className="flex items-center gap-4">
        <button 
          onClick={() => router.back()}
          className="p-2 hover:bg-gray-100 rounded-full transition-colors text-brand-dark"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold text-brand-dark">Evaluation Report Breakdown</h1>
      </div>
      
      {/* 1. Student Summary Banner */}
      <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col lg:flex-row justify-between items-center gap-8">
         {/* Name & Subject */}
         <div className="flex items-center gap-6">
            <div className="w-20 h-20 bg-brand-surface rounded-full flex items-center justify-center text-brand-dark text-2xl font-bold">
              {metadata.student_name ? metadata.student_name.split(' ').map((n: string) => n[0]).join('').substring(0, 2).toUpperCase() : 'ST'}
            </div>
            <div>
              <h1 className="text-3xl font-bold text-brand-dark">{metadata.student_name || submission?.student_name}</h1>
              <p className="text-gray-500 font-medium mt-1">Roll Number: {metadata.student_roll_number || submission?.student_roll_number}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs font-bold px-2.5 py-1 bg-brand-secondary/40 text-brand-dark rounded-full">
                  Exam ID: {metadata.exam_id?.substring(0, 8) || 'N/A'}
                </span>
                <span className="text-xs font-bold px-2.5 py-1 bg-green-50 text-brand-primary rounded-full">
                  AI Evaluated
                </span>
              </div>
            </div>
         </div>
         {/* Metrics */}
         <div className="flex flex-wrap lg:flex-nowrap gap-4 w-full lg:w-auto">
            <div className="bg-brand-background px-6 py-4 rounded-2xl border border-gray-100 flex-1 lg:flex-none">
              <p className="text-sm font-semibold text-gray-500 mb-1">Total Marks</p>
              <p className="text-2xl font-bold text-brand-dark">{totalScore} <span className="text-sm text-gray-400 font-medium">/ {maxScore}</span></p>
            </div>
            <div className="bg-brand-background px-6 py-4 rounded-2xl border border-gray-100 flex-1 lg:flex-none">
              <p className="text-sm font-semibold text-gray-500 mb-1">Percentage</p>
              <p className="text-2xl font-bold text-brand-accent">{percentage}%</p>
            </div>
            <div className="bg-brand-primary px-8 py-4 rounded-2xl shadow-[0_10px_30px_rgba(134,183,123,0.3)] flex-1 lg:flex-none flex items-center justify-between gap-6 min-w-[160px]">
              <div>
                <p className="text-sm font-semibold text-white/80 mb-1">Grade</p>
                <p className="text-4xl font-extrabold text-white">{grade}</p>
              </div>
              <Award className="w-12 h-12 text-white/50" />
            </div>
         </div>
      </div>

      {/* 2. Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left: Charts Column */}
        <div className="lg:col-span-2 space-y-8">
           
           {/* Bar Chart: Question vs Marks */}
           <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
             <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-brand-dark">Question vs Marks</h2>
             </div>
             <div className="h-[300px] w-full">
               <ResponsiveContainer width="100%" height="100%">
                 <BarChart data={barData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                   <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F3F4F6" />
                   <XAxis dataKey="question" axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} dy={10} />
                   <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                   <Tooltip 
                     cursor={{ fill: '#EEF7E8' }}
                     contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(47,90,58,0.1)' }}
                   />
                   <Bar dataKey="marks" fill="#86B77B" radius={[6, 6, 0, 0]} maxBarSize={40} />
                 </BarChart>
               </ResponsiveContainer>
             </div>
           </div>

           {/* Distribution & Performance Summary (Split Row) */}
           <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Pie Chart */}
              <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col items-center">
                 <h2 className="text-xl font-bold text-brand-dark mb-2 w-full text-left">Accuracy Distribution</h2>
                 <div className="h-[220px] w-full relative">
                   <ResponsiveContainer width="100%" height="100%">
                     <PieChart>
                       <Pie
                         data={pieData}
                         innerRadius={65}
                         outerRadius={85}
                         paddingAngle={5}
                         dataKey="value"
                         stroke="none"
                       >
                         {pieData.map((entry, index) => (
                           <Cell key={`cell-${index}`} fill={entry.color} />
                         ))}
                       </Pie>
                       <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }} />
                     </PieChart>
                   </ResponsiveContainer>
                   <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                     <span className="text-3xl font-extrabold text-brand-dark">{percentage}%</span>
                   </div>
                 </div>
                 {/* Legend */}
                 <div className="flex gap-4 mt-4 w-full justify-center">
                    {pieData.map(item => (
                      <div key={item.name} className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                        <span className="text-sm font-medium text-gray-500">{item.name}</span>
                      </div>
                    ))}
                 </div>
              </div>

              {/* Strengths / Weaknesses */}
              <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
                 <h2 className="text-xl font-bold text-brand-dark mb-6">Performance Profile</h2>
                 
                 <div className="space-y-6">
                   <div>
                     <div className="flex items-center gap-2 mb-3">
                       <Target className="w-5 h-5 text-brand-primary" />
                       <h3 className="font-semibold text-brand-dark">Strengths</h3>
                     </div>
                     <div className="flex flex-wrap gap-2">
                       {strengths.length > 0 ? strengths.map((item: string, idx: number) => (
                         <span key={idx} className="px-3 py-1.5 bg-[#EEF7E8] text-brand-dark rounded-lg text-sm font-semibold border border-brand-primary/20">{item}</span>
                       )) : (
                         <span className="text-sm text-gray-400">No specific strengths highlighted.</span>
                       )}
                     </div>
                   </div>
                   
                   <div>
                     <div className="flex items-center gap-2 mb-3 mt-6">
                       <AlertTriangle className="w-5 h-5 text-[#F87171]" />
                       <h3 className="font-semibold text-brand-dark">Weak Areas</h3>
                     </div>
                     <div className="flex flex-wrap gap-2">
                       {weaknesses.length > 0 ? weaknesses.map((item: string, idx: number) => (
                         <span key={idx} className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-sm font-semibold border border-red-200">{item}</span>
                       )) : (
                         <span className="text-sm text-gray-400">No significant weak areas identified.</span>
                       )}
                     </div>
                   </div>
                 </div>
              </div>
           </div>

        </div>

        {/* Right: AI Insights */}
        <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-3 bg-brand-accent/10 rounded-xl">
              <Brain className="w-6 h-6 text-brand-accent" />
            </div>
            <h2 className="text-xl font-bold text-brand-dark">AI Insights</h2>
          </div>
          
          <div className="flex-1 space-y-6">
            <div className="bg-brand-background rounded-2xl p-6 border border-brand-accent/20 relative overflow-hidden group hover:border-brand-accent/50 transition-colors">
              <div className="absolute top-0 left-0 w-1.5 h-full bg-brand-accent" />
              <h4 className="font-bold text-brand-dark flex items-center gap-2 mb-3">
                <Lightbulb className="w-5 h-5 text-brand-accent" /> Evaluator Summary
              </h4>
              <p className="text-sm text-gray-600 leading-relaxed">
                {evalSummary.summary || 'No evaluator summary was returned by the backend.'}
              </p>
            </div>

            <div className="bg-brand-background rounded-2xl p-6 border border-brand-primary/20 relative overflow-hidden group hover:border-brand-primary/50 transition-colors">
              <div className="absolute top-0 left-0 w-1.5 h-full bg-brand-primary" />
              <h4 className="font-bold text-brand-dark flex items-center gap-2 mb-3">
                <Lightbulb className="w-5 h-5 text-brand-primary" /> Improvements Suggested
              </h4>
              <p className="text-sm text-gray-600 leading-relaxed">
                {formatListText(improvements, 'No improvement suggestions were returned by the backend.')}
              </p>
            </div>
          </div>

          <div className="flex gap-4 mt-8">
            <button 
              onClick={handleDownloadPDF}
              className="flex-1 bg-brand-background text-brand-dark font-bold py-4 rounded-xl border border-gray-200 hover:bg-gray-100 transition-colors flex items-center justify-center gap-2"
            >
              <Download className="w-5 h-5" />
              Download PDF Report
            </button>
            <button 
              onClick={() => router.push(`/feedback?submissionId=${selectedSubmissionId}`)}
              className="flex-1 bg-brand-primary text-white font-bold py-4 rounded-xl hover:bg-opacity-90 active:scale-95 transition-all shadow-[0_10px_30px_rgba(134,183,123,0.3)]"
            >
              Detailed Feedback
            </button>
          </div>
        </div>

      </div>

      {/* 3. Question Wise Table */}
      <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
        <h2 className="text-xl font-bold text-brand-dark mb-6">Question Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b-2 border-gray-100">
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider w-1/5">Question</th>
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider w-28">Status</th>
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider w-20">Marks</th>
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider w-32">Concept Coverage</th>
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider w-24">Confidence</th>
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider">AI Feedback &amp; Concepts</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {questions.map((row: any, idx: number) => {
                const score = row.score_awarded ?? 0;
                const max = row.max_marks ?? 1;
                const status = score === max ? 'Correct' : score > 0 ? 'Partial' : 'Incorrect';
                const coverage = row.concept_coverage;
                const confidence = row.confidence;
                const matched: string[] = Array.isArray(row.matched_keywords) ? row.matched_keywords : [];
                const missing: string[] = Array.isArray(row.missing_concepts) ? row.missing_concepts : [];

                return (
                  <tr key={idx} className="hover:bg-brand-background/50 transition-colors align-top">
                    <td className="py-5 pr-4 font-semibold text-brand-dark">Question {row.question_number}</td>
                    <td className="py-5">
                      <span className={`px-3 py-1.5 rounded-full text-xs font-bold ${
                        status === 'Correct' ? 'bg-[#EEF7E8] text-[#2F5A3A]' :
                        status === 'Partial' ? 'bg-blue-50 text-blue-700' :
                        'bg-red-50 text-red-700'
                      }`}>
                        {status}
                      </span>
                    </td>
                    <td className="py-5 font-bold text-brand-dark">{score} / {max}</td>
                    <td className="py-5">
                      {coverage !== null && coverage !== undefined ? (
                        <div className="flex items-center gap-2 w-24">
                          <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-brand-primary rounded-full"
                              style={{ width: `${Math.max(0, Math.min(100, coverage))}%` }}
                            />
                          </div>
                          <span className="text-xs font-bold text-brand-dark shrink-0">{Math.round(coverage)}%</span>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">N/A</span>
                      )}
                    </td>
                    <td className="py-5">
                      {confidence !== null && confidence !== undefined ? (
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                          confidence >= 0.85 ? 'bg-[#EEF7E8] text-[#2F5A3A]' :
                          confidence >= 0.7 ? 'bg-blue-50 text-blue-700' :
                          'bg-amber-50 text-amber-700'
                        }`}>
                          {Math.round(confidence * 100)}%
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">N/A</span>
                      )}
                    </td>
                    <td className="py-5 text-sm text-gray-600 leading-relaxed pr-4">
                      <p>{row.criteria_feedback || 'Evaluation feedback is not available for this question.'}</p>
                      {(matched.length > 0 || missing.length > 0) && (
                        <div className="mt-3 flex flex-col gap-2">
                          {matched.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mr-1">Matched:</span>
                              {matched.map((concept, cIdx) => (
                                <span key={cIdx} className="px-2 py-0.5 bg-[#EEF7E8] text-[#2F5A3A] rounded text-xs font-semibold">
                                  {concept}
                                </span>
                              ))}
                            </div>
                          )}
                          {missing.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mr-1">Missing:</span>
                              {missing.map((concept, cIdx) => (
                                <span key={cIdx} className="px-2 py-0.5 bg-red-50 text-red-700 rounded text-xs font-semibold">
                                  {concept}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
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

export default function ResultsDashboard() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-brand-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-primary border-t-transparent"></div>
      </div>
    }>
      <ResultsContent />
    </Suspense>
  );
}



