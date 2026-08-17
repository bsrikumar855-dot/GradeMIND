'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  FileText, 
  Users, 
  Brain, 
  Award, 
  TrendingUp, 
  UploadCloud, 
  BarChart3, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  ArrowRight,
  Sparkles,
  Zap
} from 'lucide-react';
import { DashboardService } from '@/services/dashboard.service';
import { SubmissionService } from '@/services/submission.service';
import { ExamService } from '@/services/exam.service';

interface SubmissionItem {
  id: string;
  exam_id: string;
  student_name: string;
  student_roll_number: string;
  created_at: string;
  status: string;
  obtained_marks?: number;
  total_marks?: number;
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<any>(null);
  const [monitoring, setMonitoring] = useState<any>(null);
  const [recentSubmissions, setRecentSubmissions] = useState<SubmissionItem[]>([]);
  const [examsMap, setExamsMap] = useState<Record<string, { title: string; subject: string }>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoading(true);
        const [overviewRes, monitoringRes, submissionsRes, examsRes] = await Promise.all([
          DashboardService.getOverview(),
          DashboardService.getMonitoring(),
          SubmissionService.getSubmissions({ limit: 10 }),
          ExamService.getExams()
        ]);

        if (overviewRes.success) setOverview(overviewRes.data);
        if (monitoringRes.success) setMonitoring(monitoringRes.data);

        const mapping: Record<string, { title: string; subject: string }> = {};
        if (examsRes.success && Array.isArray(examsRes.data)) {
          examsRes.data.forEach((exam: any) => {
            mapping[exam.id] = { title: exam.title, subject: exam.subject };
          });
          setExamsMap(mapping);
        }

        if (submissionsRes.success && submissionsRes.data) {
          const list = Array.isArray(submissionsRes.data.submissions) 
            ? submissionsRes.data.submissions 
            : (Array.isArray(submissionsRes.data) ? submissionsRes.data : []);
          setRecentSubmissions(list);
        }
      } catch (err: any) {
        console.error('Failed to load dashboard data:', err);
        setError('Could not retrieve dashboard analytics. Please verify backend connectivity.');
      } finally {
        setLoading(false);
      }
    }

    loadDashboardData();
  }, []);

  const formatPercentage = (val?: number) => {
    if (val === undefined || val === null) return '--%';
    const normalized = val <= 1 && val > 0 ? val * 100 : val;
    return `${normalized.toFixed(1)}%`;
  };

  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" /> Evaluated
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 border border-rose-500/20">
            <AlertCircle className="w-3.5 h-3.5" /> Error
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 border border-amber-500/20 animate-pulse">
            <Clock className="w-3.5 h-3.5" /> Processing
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[65vh] space-y-4">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20"></div>
          <div className="absolute inset-0 rounded-full border-4 border-emerald-500 border-t-transparent animate-spin"></div>
        </div>
        <p className="text-slate-500 font-semibold text-sm animate-pulse">Loading GradeMIND Analytics Dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto mt-12 p-8 glass-card rounded-3xl border border-rose-200 text-center space-y-4">
        <div className="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">Backend Connection Notice</h2>
        <p className="text-slate-600 text-sm max-w-md mx-auto">{error}</p>
        <button 
          onClick={() => window.location.reload()} 
          className="px-6 py-2.5 bg-slate-900 text-white font-bold text-sm rounded-xl hover:bg-slate-800 transition-all shadow-lg shadow-slate-900/20"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const totalExams = overview?.total_exams ?? 0;
  const totalSubmissions = overview?.total_submissions ?? 0;
  const evaluatedSubmissions = overview?.evaluated_submissions ?? 0;
  const averageScore = overview?.average_score ?? 0;
  const averageConfidence = overview?.average_confidence ?? 0;
  const scoreDistribution = monitoring?.score_distribution || {};
  const scoreBars = [
    { label: '90-100%', count: scoreDistribution['90-100'] || 0, color: '#10B981' },
    { label: '80-89%', count: scoreDistribution['80-89'] || 0, color: '#3B82F6' },
    { label: '70-79%', count: scoreDistribution['70-79'] || 0, color: '#8B5CF6' },
    { label: '60-69%', count: scoreDistribution['60-69'] || 0, color: '#F59E0B' },
    { label: '<60%', count: scoreDistribution.below_60 || 0, color: '#EF4444' },
  ];
  const maxScoreBucket = Math.max(...scoreBars.map((b) => b.count), 1);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      
      {/* Welcome & AI Engine Banner */}
      <div className="relative overflow-hidden glass-card rounded-3xl p-8 bg-gradient-to-r from-slate-900 via-slate-800 to-emerald-950 text-white shadow-2xl border border-slate-700/50">
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
        
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold uppercase tracking-wider mb-3">
              <Sparkles className="w-3.5 h-3.5" /> Autonomous AI Examiner
            </div>
            <h1 className="text-3xl font-black tracking-tight text-white">
              Evaluation & Analytics Overview
            </h1>
            <p className="text-slate-300 text-sm mt-1 max-w-xl">
              GradeMIND uses Groq 120B & Gemini Vision AI to grade answer sheets with human-examiner rigor in under 1.5 seconds per script.
            </p>
          </div>

          <div className="flex gap-3">
            <Link 
              href="/upload" 
              className="px-5 py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm rounded-xl transition-all shadow-lg shadow-emerald-500/30 flex items-center gap-2"
            >
              <UploadCloud className="w-4 h-4" /> Upload Exam Sheet
            </Link>
            <Link 
              href="/results" 
              className="px-5 py-3 bg-white/10 hover:bg-white/20 text-white font-bold text-sm rounded-xl transition-all border border-white/20 backdrop-blur-md flex items-center gap-2"
            >
              View Results <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* 1. KPI Cards Row (21st.dev Style Glassmorphism) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* Total Exams */}
        <div className="glass-card glass-card-hover rounded-2xl p-6 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Exams</span>
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-600 flex items-center justify-center">
              <FileText className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-slate-900">{totalExams}</span>
            <span className="block text-xs font-semibold text-slate-500 mt-1">Configured Exam Packages</span>
          </div>
        </div>

        {/* Submissions Uploaded */}
        <div className="glass-card glass-card-hover rounded-2xl p-6 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Submissions</span>
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-600 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-slate-900">{totalSubmissions}</span>
            <span className="block text-xs font-semibold text-emerald-600 mt-1">{evaluatedSubmissions} Evaluated & Scored</span>
          </div>
        </div>

        {/* AI Confidence */}
        <div className="glass-card glass-card-hover rounded-2xl p-6 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">AI Confidence</span>
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center">
              <Brain className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-emerald-600">{formatPercentage(averageConfidence)}</span>
            <span className="block text-xs font-semibold text-slate-500 mt-1">OCR & Evaluation Precision</span>
          </div>
        </div>

        {/* Class Average */}
        <div className="glass-card glass-card-hover rounded-2xl p-6 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Class Average</span>
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-600 flex items-center justify-center">
              <Award className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-black text-slate-900">{formatPercentage(averageScore)}</span>
            <span className="block text-xs font-semibold text-slate-500 mt-1">Overall Student Mastery</span>
          </div>
        </div>

      </div>

      {/* 2. Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left 2 Columns: Score Distribution & Submissions Table */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Score Distribution Chart */}
          <div className="glass-card rounded-3xl p-6 md:p-8">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Score Distribution</h2>
                <p className="text-xs text-slate-400">Student performance across score bands</p>
              </div>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-emerald-500" /> Real-time Analytics
              </span>
            </div>

            {/* Custom Bar Visualization */}
            <div className="space-y-4">
              {scoreBars.map((bucket) => {
                const pct = Math.round((bucket.count / maxScoreBucket) * 100);
                return (
                  <div key={bucket.label} className="space-y-1.5">
                    <div className="flex justify-between text-xs font-bold text-slate-700">
                      <span>{bucket.label}</span>
                      <span className="text-slate-500">{bucket.count} student(s) ({pct}%)</span>
                    </div>
                    <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200/50">
                      <div 
                        className="h-full rounded-full transition-all duration-700 ease-out" 
                        style={{ width: `${Math.max(pct, 4)}%`, backgroundColor: bucket.color }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recent Submissions Table */}
          <div className="glass-card rounded-3xl p-6 md:p-8">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Recent Answer Sheets</h2>
                <p className="text-xs text-slate-400">Latest student submissions processed by GradeMIND</p>
              </div>
              <Link href="/results" className="text-xs font-bold text-emerald-600 hover:text-emerald-700 flex items-center gap-1">
                View All <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    <th className="pb-3">Student & Roll No.</th>
                    <th className="pb-3">Exam / Subject</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {recentSubmissions.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-400 text-sm">
                        No submissions evaluated yet. Click Upload Exam Sheet to start!
                      </td>
                    </tr>
                  ) : (
                    recentSubmissions.map((sub) => {
                      const examInfo = examsMap[sub.exam_id] || { title: 'Exam', subject: 'General' };
                      return (
                        <tr key={sub.id} className="group hover:bg-slate-50/80 transition-colors">
                          <td className="py-4">
                            <div className="font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">{sub.student_name}</div>
                            <div className="text-xs text-slate-400 font-medium">{sub.student_roll_number || 'N/A'}</div>
                          </td>
                          <td className="py-4">
                            <div className="font-semibold text-slate-700 text-xs">{examInfo.title}</div>
                            <div className="text-[11px] text-slate-400">{examInfo.subject}</div>
                          </td>
                          <td className="py-4">
                            {getStatusBadge(sub.status)}
                          </td>
                          <td className="py-4 text-right font-black text-slate-900">
                            {sub.obtained_marks !== undefined && sub.obtained_marks !== null && sub.total_marks
                              ? `${sub.obtained_marks} / ${sub.total_marks}`
                              : '--'}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Right Column: Quick Actions & Reports */}
        <div className="space-y-8">
          
          {/* Quick Action Shortcuts */}
          <div className="glass-card rounded-3xl p-6">
            <h2 className="text-lg font-bold text-slate-900 mb-4">Quick Actions</h2>
            <div className="grid grid-cols-2 gap-3">
              <Link 
                href="/upload" 
                className="p-4 rounded-2xl bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-200/60 hover:border-emerald-500/50 hover:shadow-md transition-all group flex flex-col items-center text-center"
              >
                <div className="w-10 h-10 rounded-xl bg-emerald-500 text-white flex items-center justify-center mb-2 group-hover:scale-110 transition-transform shadow-md shadow-emerald-500/20">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <span className="text-xs font-bold text-slate-900">Upload Exam</span>
              </Link>

              <Link 
                href="/reports" 
                className="p-4 rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200/60 hover:border-blue-500/50 hover:shadow-md transition-all group flex flex-col items-center text-center"
              >
                <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center mb-2 group-hover:scale-110 transition-transform shadow-md shadow-blue-500/20">
                  <BarChart3 className="w-5 h-5" />
                </div>
                <span className="text-xs font-bold text-slate-900">Analytics</span>
              </Link>
            </div>
          </div>

          {/* AI System Status */}
          <div className="glass-card rounded-3xl p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-slate-900 text-emerald-400 flex items-center justify-center">
                <Zap className="w-5 h-5 fill-emerald-400" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">Groq 120B LLM Active</h3>
                <p className="text-xs text-slate-400">Sub-second academic reasoning</p>
              </div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-100/80 text-xs font-medium text-slate-600 leading-relaxed">
              Evaluating student answers against marking rubrics using 120B parameter vision & LLM inference.
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
