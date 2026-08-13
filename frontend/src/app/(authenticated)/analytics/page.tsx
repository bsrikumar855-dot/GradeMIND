'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Brain, Award, AlertTriangle, ArrowLeft, Target, Lightbulb, TrendingUp } from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';

function AnalyticsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const submissionId = searchParams.get('submissionId') || searchParams.get('id');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [selectedSubId, setSelectedSubId] = useState<string>('');
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    async function loadInitial() {
      try {
        setLoading(true);
        const res = await SubmissionService.getEvaluatedSubmissions();
        const list = res.data || [];
        setSubmissions(list);

        if (list.length > 0) {
          const matched = list.find((s: any) => s.id === submissionId) || list[0];
          setSelectedSubId(matched.id);
        } else {
          setError('No evaluated submissions are available yet.');
        }
      } catch (err: any) {
        console.error('Failed to load submissions:', err);
        setError('Failed to fetch evaluated submissions.');
      } finally {
        setLoading(false);
      }
    }
    loadInitial();
  }, [submissionId]);

  useEffect(() => {
    if (!selectedSubId) return;

    async function loadReport() {
      try {
        setLoading(true);
        setError('');
        const res = await SubmissionService.getReport(selectedSubId);
        if (res.success && res.data) {
          setReport(res.data);
        } else {
          setError('Failed to load analytics report.');
        }
      } catch (err: any) {
        console.error('Failed to fetch report:', err);
        setError('Failed to retrieve evaluation report.');
      } finally {
        setLoading(false);
      }
    }
    loadReport();
  }, [selectedSubId]);

  const handleSubChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedSubId(val);
    router.replace(`/analytics?submissionId=${val}`);
  };

  if (loading && !report) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-brand-primary border-t-transparent"></div>
        <p className="text-gray-500 font-semibold">Compiling learning intelligence...</p>
      </div>
    );
  }

  const evalSummary = report?.evaluation_summary || {};
  const analytics = evalSummary.learning_analytics;
  const metadata = report?.metadata || {};

  const getStatusColor = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'MASTERED':
        return 'bg-[#EEF7E8] text-[#2F5A3A] border-[#2F5A3A]/20';
      case 'DEVELOPING':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'WEAK':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'CRITICAL':
        return 'bg-red-50 text-red-700 border-red-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  const getSeverityColor = (sev: string) => {
    switch (sev?.toUpperCase()) {
      case 'HIGH':
        return 'bg-red-50 text-red-700 border-red-200';
      case 'MEDIUM':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'LOW':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.push('/dashboard')}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors text-brand-dark"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-brand-dark flex items-center gap-3">
              <div className="p-2 bg-brand-primary/10 rounded-xl">
                <Brain className="w-6 h-6 text-brand-primary" />
              </div>
              Student Learning Analytics
            </h1>
            <p className="text-gray-500 mt-2 font-medium">Observational analytics and topic-level mastery gaps.</p>
          </div>
        </div>

        {/* Dropdown Selector */}
        {submissions.length > 0 && (
          <div className="relative w-full md:w-72">
            <select
              value={selectedSubId}
              onChange={handleSubChange}
              className="appearance-none w-full pl-4 pr-10 py-3 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all shadow-sm text-brand-dark font-semibold text-sm cursor-pointer"
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

      {error && (
        <div className="p-5 bg-red-50 border border-red-200 rounded-2xl text-red-700 flex items-center gap-3">
          <AlertTriangle className="w-6 h-6" />
          <span className="font-semibold">{error}</span>
        </div>
      )}

      {report && (
        <>
          {/* Metadata Card */}
          <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col md:flex-row justify-between items-center gap-6">
            <div className="flex items-center gap-6">
              <div className="w-16 h-16 bg-brand-surface rounded-full flex items-center justify-center text-brand-dark text-xl font-bold">
                {metadata.student_name ? metadata.student_name.split(' ').map((n: string) => n[0]).join('').substring(0,2).toUpperCase() : 'ST'}
              </div>
              <div>
                <h2 className="text-2xl font-bold text-brand-dark">{metadata.student_name}</h2>
                <p className="text-sm text-gray-500 font-medium mt-0.5">Roll Number: {metadata.student_roll_number}</p>
              </div>
            </div>
            {analytics && (
              <div className="bg-brand-primary px-8 py-4 rounded-2xl shadow-[0_10px_30px_rgba(134,183,123,0.3)] flex items-center justify-between gap-6 min-w-[220px]">
                <div>
                  <p className="text-xs font-semibold text-white/80 mb-1">Overall Mastery</p>
                  <p className="text-3xl font-extrabold text-white">
                    {Math.round(analytics.overall_mastery * 100)}%
                  </p>
                </div>
                <TrendingUp className="w-10 h-10 text-white/50" />
              </div>
            )}
          </div>

          {analytics ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left Column: Topic Mastery */}
              <div className="lg:col-span-2 space-y-8">
                {/* Mastery Grid */}
                <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
                  <h3 className="text-lg font-bold text-brand-dark mb-6 flex items-center gap-2">
                    <Target className="w-5 h-5 text-brand-primary" /> Topic Mastery Scorecard
                  </h3>
                  
                  {/* Mock/Retrieved Topics list from Analytics Service */}
                  <div className="space-y-6">
                    {/* If mastered_topics and weak_topics lists exist, render a clean combined list */}
                    {analytics.weak_topics?.length === 0 && analytics.mastered_topics?.length === 0 ? (
                      <p className="text-gray-400 text-sm">No topics detected in curriculum context.</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {analytics.mastered_topics?.map((topic: string) => (
                          <div key={topic} className="p-4 rounded-xl border border-[#2F5A3A]/20 bg-[#EEF7E8]/20 flex flex-col justify-between">
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-[#2F5A3A]">Mastered</span>
                              <h4 className="font-bold text-brand-dark mt-1 text-sm">{topic}</h4>
                            </div>
                            <div className="mt-4 flex items-center justify-between text-xs font-semibold text-[#2F5A3A]">
                              <span>Mastery Level</span>
                              <span>High / 85%+</span>
                            </div>
                          </div>
                        ))}

                        {analytics.weak_topics?.map((topic: string) => (
                          <div key={topic} className="p-4 rounded-xl border border-red-200 bg-red-50/20 flex flex-col justify-between">
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-red-600">Needs Practice</span>
                              <h4 className="font-bold text-brand-dark mt-1 text-sm">{topic}</h4>
                            </div>
                            <div className="mt-4 flex items-center justify-between text-xs font-semibold text-red-600">
                              <span>Mastery Level</span>
                              <span>Critical / Below 50%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Knowledge Gaps Card */}
                <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
                  <h3 className="text-lg font-bold text-brand-dark mb-6 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-brand-accent" /> Identified Knowledge Gaps
                  </h3>
                  <div className="space-y-4">
                    {analytics.knowledge_gaps && analytics.knowledge_gaps.length > 0 ? (
                      analytics.knowledge_gaps.map((gap: any, idx: number) => (
                        <div key={idx} className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 flex flex-col md:flex-row justify-between md:items-center gap-4">
                          <div>
                            <h4 className="font-bold text-brand-dark text-sm">{gap.topic}</h4>
                            <div className="flex flex-wrap gap-1.5 mt-2">
                              {gap.missing_concepts?.map((c: string) => (
                                <span key={c} className="px-2.5 py-1 bg-white border border-gray-200 text-gray-600 rounded text-[11px] font-semibold">
                                  {c}
                                </span>
                              ))}
                            </div>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-xs font-bold border self-start md:self-center ${getSeverityColor(gap.severity)}`}>
                            {gap.severity} severity gap
                          </span>
                        </div>
                      ))
                    ) : (
                      <p className="text-gray-400 text-sm">No conceptual knowledge gaps detected. Great job!</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Recommendations */}
              <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col">
                <h3 className="text-lg font-bold text-brand-dark mb-6 flex items-center gap-2">
                  <Lightbulb className="w-5 h-5 text-brand-accent" /> Actionable Recommendations
                </h3>
                <div className="space-y-4 flex-1">
                  {analytics.recommendations && analytics.recommendations.length > 0 ? (
                    analytics.recommendations.map((rec: string, idx: number) => (
                      <div key={idx} className="p-4 rounded-xl border border-brand-accent/20 bg-brand-background relative overflow-hidden">
                        <div className="absolute left-0 top-0 w-1 h-full bg-brand-accent" />
                        <p className="text-xs text-gray-600 font-semibold uppercase tracking-wider mb-1">Step {idx + 1}</p>
                        <p className="text-sm text-brand-dark leading-relaxed font-semibold">
                          {rec}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-gray-400 text-sm">No study recommendations available.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center bg-white rounded-3xl border border-gray-100 shadow-sm">
              <p className="text-gray-500 font-semibold">Detailed Learning Analytics are not populated for this older report record.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-brand-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-primary border-t-transparent"></div>
      </div>
    }>
      <AnalyticsContent />
    </Suspense>
  );
}
