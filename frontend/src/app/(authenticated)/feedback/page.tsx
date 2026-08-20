'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import { Sparkles, Target, AlertTriangle, BookOpen, Lightbulb, ArrowRight, Brain, ArrowLeft } from 'lucide-react';
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

function FeedbackContent() {
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
          router.replace(`/feedback?submissionId=${activeSubmissionId}`);
        } else {
          setSelectedSubmissionId(activeSubmissionId);
        }
        const resolvedSubmissionId = activeSubmissionId as string;

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
          setError('Failed to retrieve feedback details.');
        }
      } catch (err: any) {
        console.error('Failed to load feedback details:', err);
        setError(err.response?.data?.detail || 'Feedback data is currently not available.');
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
        <p className="text-gray-500 font-semibold">Synthesizing personalized AI feedback...</p>
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
            <h1 className="text-2xl font-bold text-brand-dark mb-2">Feedback Center</h1>
            <p className="text-gray-500 max-w-md mx-auto">{error || 'Unable to retrieve the developmental roadmap for this student.'}</p>
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
  const metadata = report.metadata || {};
  const strengths = normalizeList(evalSummary.strengths);
  const weaknesses = normalizeList(evalSummary.weaknesses);
  const improvements = normalizeList(evalSummary.improvements);
  const recommendations = normalizeList(evalSummary.recommendations || evalSummary.study_recommendations);

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

  return (
    <div className="p-4 lg:p-6 w-full max-w-full space-y-6">
      
      {/* Navigation Header */}
      <div className="flex items-center gap-4">
        <button 
          onClick={() => router.back()}
          className="p-2 hover:bg-gray-100 rounded-full transition-colors text-brand-dark"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        <h1 className="text-xl font-bold text-brand-dark">Detailed AI Feedback Report</h1>
      </div>

      {/* 1. Hero / AI Welcome Card */}
      <div className="bg-brand-secondary rounded-[24px] overflow-hidden shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col relative min-h-[400px]">
        {/* Full-span Background Illustration */}
        <div className="absolute inset-0 w-full h-full z-0 pointer-events-none opacity-20 overflow-hidden">
          <div className="absolute right-0 bottom-0 w-[500px] h-[500px] bg-brand-primary/10 rounded-full filter blur-3xl"></div>
          <div className="absolute right-20 top-10 w-[300px] h-[300px] bg-brand-accent/10 rounded-full filter blur-2xl"></div>
        </div>

        <div className="p-10 md:w-2/3 lg:w-1/2 flex flex-col justify-center relative z-10 bg-white/85 backdrop-blur-md h-full min-h-[400px] border-r border-white/50">
          <div className="flex items-center gap-3 mb-6">
             <div className="p-2 bg-brand-primary/10 rounded-xl">
               <Sparkles className="w-5 h-5 text-brand-primary" />
             </div>
             <span className="text-xs font-bold text-brand-primary uppercase tracking-widest">AI Feedback Report</span>
          </div>
          <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-brand-dark mb-6 leading-tight">
            Personalized Insights for <br/>
            <span className="text-brand-accent">{metadata.student_name || submission?.student_name}</span>
          </h1>
          <p className="text-gray-600 text-lg max-w-xl leading-relaxed">
            {evalSummary.summary || 'No evaluator summary was returned by the backend.'}
          </p>
          <div className="mt-10">
            <button 
              onClick={handleDownloadPDF}
              className="bg-brand-primary text-white font-bold py-4 px-8 rounded-xl hover:bg-opacity-90 active:scale-95 transition-all shadow-[0_10px_30px_rgba(134,183,123,0.3)] flex items-center gap-2 w-fit"
            >
              <BookOpen className="w-5 h-5" />
              Download Study Plan PDF
            </button>
          </div>
        </div>
      </div>

      {/* 2. Main Analytics & Feedback Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Strengths & Weaknesses */}
        <div className="lg:col-span-1 space-y-8">
          
          <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 border-t-4 border-t-brand-primary relative overflow-hidden group">
            <div className="absolute -right-6 -top-6 w-24 h-24 bg-brand-primary/5 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-700" />
            <div className="flex items-center gap-3 mb-8 relative z-10">
              <div className="w-12 h-12 rounded-full bg-[#EEF7E8] flex items-center justify-center">
                <Target className="w-6 h-6 text-brand-primary" />
              </div>
              <h2 className="text-2xl font-bold text-brand-dark">Core Strengths</h2>
            </div>
            <ul className="space-y-6 relative z-10">
              {strengths.length > 0 ? strengths.map((strength: string, idx: number) => {
                const parts = strength.split(':');
                const title = parts[0];
                const desc = parts.slice(1).join(':').trim();

                return (
                  <li key={idx} className="flex gap-4">
                    <div className="mt-1.5 flex-shrink-0 w-2.5 h-2.5 rounded-full bg-brand-primary shadow-[0_0_10px_rgba(134,183,123,0.8)]" />
                    <p className="text-gray-600 text-sm leading-relaxed">
                      <strong className="text-brand-dark block text-base mb-1">{title}</strong>
                      {desc || 'Demonstrated high competence and accuracy.'}
                    </p>
                  </li>
                );
              }) : (
                <li className="text-gray-400 text-sm italic">No specific strengths mapped.</li>
              )}
            </ul>
          </div>

          <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 border-t-4 border-t-[#F87171] relative overflow-hidden group">
            <div className="absolute -right-6 -top-6 w-24 h-24 bg-red-500/5 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-700" />
            <div className="flex items-center gap-3 mb-8 relative z-10">
              <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-[#F87171]" />
              </div>
              <h2 className="text-2xl font-bold text-brand-dark">Weak Areas</h2>
            </div>
            <ul className="space-y-6 relative z-10">
              {weaknesses.length > 0 ? weaknesses.map((weakness: string, idx: number) => {
                const parts = weakness.split(':');
                const title = parts[0];
                const desc = parts.slice(1).join(':').trim();

                return (
                  <li key={idx} className="flex gap-4">
                    <div className="mt-1.5 flex-shrink-0 w-2.5 h-2.5 rounded-full bg-[#F87171] shadow-[0_0_10px_rgba(248,113,113,0.8)]" />
                    <p className="text-gray-600 text-sm leading-relaxed">
                      <strong className="text-brand-dark block text-base mb-1">{title}</strong>
                      {desc || 'Requires thorough concept revision and practice.'}
                    </p>
                  </li>
                );
              }) : (
                <li className="text-gray-400 text-sm italic">No specific weak areas mapped.</li>
              )}
            </ul>
          </div>

        </div>

        {/* Right Column: Performance Analysis & Suggestions */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Performance Analysis */}
          <div className="bg-white rounded-[24px] p-10 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 relative overflow-hidden h-fit">
             {/* Decorative watermark */}
             <Brain className="absolute -bottom-16 -right-16 w-96 h-96 text-brand-background opacity-60 z-0 pointer-events-none" />
             
             <div className="relative z-10">
                <h2 className="text-2xl font-bold text-brand-dark mb-8 flex items-center gap-3">
                  <div className="p-2 bg-brand-accent/10 rounded-xl">
                    <Brain className="w-6 h-6 text-brand-accent" />
                  </div>
                  Deep Performance Analysis
                </h2>
                <div className="prose prose-gray max-w-none space-y-6">
                  <p className="text-gray-600 leading-relaxed text-lg">
                    {evalSummary.summary || 'No deep performance analysis was returned by the backend.'}
                  </p>
                  <div className="bg-brand-background rounded-2xl p-6 border-l-4 border-brand-accent mt-8 shadow-inner">
                    <h4 className="font-bold text-brand-dark mb-2 text-lg">AI Action Plan</h4>
                    <p className="text-gray-600 leading-relaxed">
                      {formatListText(improvements, 'No action plan was returned by the backend.')}
                    </p>
                  </div>
                </div>
             </div>
          </div>

          {/* Actionable Suggestions & Topics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Suggestions */}
            <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col h-full">
               <h2 className="text-xl font-bold text-brand-dark mb-6 flex items-center gap-3">
                 <div className="p-2 bg-yellow-50 rounded-xl">
                   <Lightbulb className="w-6 h-6 text-yellow-500" />
                 </div>
                 Actionable Suggestions
               </h2>
               <div className="space-y-4 flex-1">
                 {improvements.length > 0 ? (
                   improvements.map((sentence: string, idx: number) => (
                     <div key={idx} className="p-5 bg-yellow-50/50 rounded-xl border border-yellow-100 hover:bg-yellow-50 transition-colors">
                       <p className="text-sm text-gray-700 font-medium leading-relaxed">{sentence.endsWith('.') ? sentence : `${sentence}.`}</p>
                     </div>
                   ))
                 ) : (
                   <div className="p-5 bg-brand-background rounded-xl border border-gray-100">
                     <p className="text-sm text-gray-400">No suggestions generated yet.</p>
                   </div>
                 )}
               </div>
            </div>

            {/* Recommended Topics */}
            <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col h-full">
               <h2 className="text-xl font-bold text-brand-dark mb-6 flex items-center gap-3">
                 <div className="p-2 bg-brand-primary/10 rounded-xl">
                   <BookOpen className="w-6 h-6 text-brand-primary" />
                 </div>
                 Recommended Topics
               </h2>
               <div className="space-y-3 flex-1">
                 {weaknesses.length > 0 ? (
                   weaknesses.map((weak: string) => splitFeedbackItem(weak).desc || splitFeedbackItem(weak).title).slice(0, 3).map((topic: string) => (
                     <div key={topic} className="flex items-center justify-between p-4 bg-brand-background hover:bg-brand-surface/20 rounded-xl transition-all cursor-pointer group border border-transparent hover:border-brand-primary/20 hover:shadow-sm">
                       <span className="font-semibold text-brand-dark text-sm">{topic}</span>
                       <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-brand-primary transition-colors transform group-hover:translate-x-1" />
                     </div>
                   ))
                 ) : (
                   <div className="p-5 bg-brand-background rounded-xl border border-gray-100">
                     <p className="text-sm text-gray-400">No recommended topics were returned by the backend.</p>
                   </div>
                 )}
               </div>
               <button className="w-full mt-6 text-sm font-bold text-brand-primary py-3 bg-brand-primary/5 hover:bg-brand-primary/10 rounded-xl transition-colors">
                 Generate Practice Quiz
               </button>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}

export default function FeedbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-brand-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-primary border-t-transparent"></div>
      </div>
    }>
      <FeedbackContent />
    </Suspense>
  );
}



