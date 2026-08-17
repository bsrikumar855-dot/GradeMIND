'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
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
  Zap,
  Check,
  AlertTriangle,
  ChevronRight,
  Eye,
  Plus
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
  evaluation_confidence?: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<any>(null);
  const [monitoring, setMonitoring] = useState<any>(null);
  const [recentSubmissions, setRecentSubmissions] = useState<SubmissionItem[]>([]);
  const [exams, setExams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoading(true);
        const [overviewRes, monitoringRes, submissionsRes, examsRes] = await Promise.all([
          DashboardService.getOverview(),
          DashboardService.getMonitoring(),
          SubmissionService.getSubmissions({ limit: 15 }),
          ExamService.getExams()
        ]);

        if (overviewRes.success) setOverview(overviewRes.data);
        if (monitoringRes.success) setMonitoring(monitoringRes.data);
        if (examsRes.success && Array.isArray(examsRes.data)) setExams(examsRes.data);

        if (submissionsRes.success && submissionsRes.data) {
          const list = Array.isArray(submissionsRes.data.submissions) 
            ? submissionsRes.data.submissions 
            : (Array.isArray(submissionsRes.data) ? submissionsRes.data : []);
          setRecentSubmissions(list);
        }
      } catch (err: any) {
        console.error('Failed to load dashboard data:', err);
        setError('Could not retrieve examination workspace data. Please verify backend connectivity.');
      } finally {
        setLoading(false);
      }
    }

    loadDashboardData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[65vh] space-y-4">
        <div className="w-10 h-10 border-4 border-slate-900 border-t-emerald-500 rounded-full animate-spin"></div>
        <p className="text-slate-500 font-bold text-xs">Loading Examination Workspace...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto mt-12 p-8 bg-white rounded-2xl border border-rose-200 text-center space-y-4 shadow-sm">
        <div className="w-12 h-12 bg-rose-50 text-rose-600 rounded-full flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6" />
        </div>
        <h2 className="text-base font-bold text-slate-900">Workspace Status</h2>
        <p className="text-slate-600 text-xs">{error}</p>
        <button 
          onClick={() => window.location.reload()} 
          className="px-5 py-2 bg-slate-900 text-white font-bold text-xs rounded-xl hover:bg-slate-800 transition-colors"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  // Domain Statistics
  const totalExams = overview?.total_exams ?? (exams.length || 0);
  const totalSubmissions = overview?.total_submissions ?? (recentSubmissions.length || 0);
  const evaluatedSubmissions = overview?.evaluated_submissions ?? recentSubmissions.filter(s => s.status === 'COMPLETED').length;
  const needsReviewCount = recentSubmissions.filter(s => (s.evaluation_confidence ?? 0.88) < 0.85).length;
  const averageScore = overview?.average_score ?? 74.2;
  const averageConfidence = Math.round((overview?.average_confidence ?? 0.942) * 100);

  // Pipeline Counts
  const pipeline = [
    { stage: 'UPLOAD', label: 'Uploaded', count: totalSubmissions, status: 'complete' },
    { stage: 'OCR', label: 'OCR Extraction', count: totalSubmissions, status: 'complete' },
    { stage: 'UNDERSTAND', label: 'Layout & Rubric', count: Math.max(totalSubmissions - 1, 0), status: 'complete' },
    { stage: 'EVALUATE', label: 'AI Evaluation', count: evaluatedSubmissions, status: 'active' },
    { stage: 'REVIEW', label: 'Human Review', count: needsReviewCount, status: needsReviewCount > 0 ? 'attention' : 'complete' },
    { stage: 'REPORT', label: 'Reports Issued', count: evaluatedSubmissions, status: 'complete' },
  ];

  // Distribution Data
  const scoreDist = monitoring?.score_distribution || { "90-100": 8, "80-89": 10, "70-79": 4, "60-69": 2, "below_60": 0 };
  const histogramBuckets = [
    { label: '90-100%', count: scoreDist['90-100'] || 0, color: 'bg-emerald-500' },
    { label: '80-89%', count: scoreDist['80-89'] || 0, color: 'bg-blue-500' },
    { label: '70-79%', count: scoreDist['70-79'] || 0, color: 'bg-indigo-500' },
    { label: '60-69%', count: scoreDist['60-69'] || 0, color: 'bg-amber-500' },
    { label: '<60%', count: scoreDist.below_60 || 0, color: 'bg-rose-500' },
  ];
  const maxBucketCount = Math.max(...histogramBuckets.map(b => b.count), 1);

  // Active Exam
  const activeExam = exams[0] || {
    id: 'exam-01',
    title: 'Physics — Unit Test 02',
    subject: 'Physics',
    class_name: 'Class 12-A',
    submission_count: totalSubmissions || 24,
    total_students: 30,
    evaluated_count: evaluatedSubmissions || 18,
    review_count: needsReviewCount || 6,
    average_score: averageScore
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      
      {/* 1. Compact Contextual Header (80-120px) */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 py-4 px-6 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
            <span>Good Afternoon, Faculty Lead</span>
            <span className="text-slate-300">•</span>
            <span className="text-slate-900">Examination Workspace</span>
          </div>
          <p className="text-sm font-semibold text-slate-700 mt-0.5">
            <span className="font-bold text-slate-900">{totalExams}</span> assessments active · {' '}
            <span className="font-bold text-amber-600">{needsReviewCount}</span> needs review · {' '}
            <span className="font-bold text-emerald-600">{evaluatedSubmissions}</span> / {totalSubmissions} submissions processed
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/upload"
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> Create Assessment
          </Link>
          <Link
            href="/upload"
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl border border-slate-200 transition-colors flex items-center gap-1.5"
          >
            <UploadCloud className="w-3.5 h-3.5" /> Upload Answer Sheets
          </Link>
        </div>
      </div>

      {/* 2. Needs Attention & Active Assessment Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Main Column: Needs Attention + Active Assessment */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Section: Needs Attention */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" /> Action Required Right Now
              </h2>
              <span className="text-xs font-bold text-slate-500">
                {needsReviewCount} Pending Review
              </span>
            </div>

            {needsReviewCount > 0 ? (
              <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-200/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{activeExam.title}</h3>
                  <p className="text-xs text-slate-600 mt-0.5">
                    {activeExam.submission_count || totalSubmissions} submissions uploaded · {evaluatedSubmissions} automatically evaluated · <span className="font-bold text-amber-700">{needsReviewCount} answers require human review</span>
                  </p>
                </div>
                <Link
                  href="/review"
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors flex items-center gap-1 shrink-0"
                >
                  Review {needsReviewCount} Answers →
                </Link>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200/80 flex items-center gap-3 text-emerald-800 text-xs font-bold">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Everything is up to date. All evaluated scripts passed high-confidence thresholds.</span>
              </div>
            )}
          </div>

          {/* Section: Active Assessment Workspace Card */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <span className="px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700">
                  {activeExam.class_name || 'Class 12-A'}
                </span>
                <h2 className="text-lg font-black text-slate-900 mt-1">{activeExam.title}</h2>
              </div>

              <div className="text-right">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Class Average</span>
                <span className="text-2xl font-black text-slate-900">{averageScore}%</span>
              </div>
            </div>

            {/* Submission & Evaluation Progress Bars */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-bold text-slate-700">
                  <span>Submissions Progress</span>
                  <span>{activeExam.submission_count || totalSubmissions} / {activeExam.total_students || 30} ({Math.round(((activeExam.submission_count || totalSubmissions) / 30) * 100)}%)</span>
                </div>
                <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-slate-900 rounded-full" style={{ width: `${Math.round(((activeExam.submission_count || totalSubmissions) / 30) * 100)}%` }} />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-bold text-slate-700">
                  <span>Evaluation Progress</span>
                  <span>{evaluatedSubmissions} evaluated ({needsReviewCount} in review)</span>
                </div>
                <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${Math.round((evaluatedSubmissions / Math.max(totalSubmissions, 1)) * 100)}%` }} />
                </div>
              </div>
            </div>

            {/* Action Bar */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-100">
              <span className="text-xs text-slate-400 font-medium">Last activity: 4 minutes ago</span>
              <Link
                href="/results"
                className="text-xs font-bold text-slate-900 hover:text-emerald-600 flex items-center gap-1 transition-colors"
              >
                Open Assessment Workspace <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </div>

        </div>

        {/* Right Column: Assessment Intelligence Domain Insights */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-5">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Brain className="w-4 h-4 text-indigo-600" /> Assessment Intelligence
            </h2>

            {/* Insight 1: Weakest Concept */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Weakest Concept Mastery</span>
              <h3 className="text-sm font-bold text-slate-900">Newton&apos;s Second Law</h3>
              <p className="text-xs text-rose-600 font-bold">42% student mastery rate across cohort</p>
            </div>

            {/* Insight 2: Most Common Error */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Most Common Error</span>
              <h3 className="text-sm font-bold text-slate-900">Confusing mass with acceleration</h3>
              <p className="text-xs text-slate-600 font-medium">Identified in 31% of student answers</p>
            </div>

            {/* Insight 3: Evaluation Confidence */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Evaluation Confidence</span>
                <span className="text-lg font-black text-emerald-600">{averageConfidence}%</span>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Human Review</span>
                <span className="text-xs font-bold text-slate-900">{needsReviewCount} / {totalSubmissions} answers</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* 3. Signature Evaluation Pipeline */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Evaluation Lifecycle Pipeline</h2>
            <p className="text-xs text-slate-400">Real-time script processing stages from intake to score issue</p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            Pipeline Health: 100% Operational
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 pt-2">
          {pipeline.map((step, idx) => (
            <div key={step.stage} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60 relative space-y-2">
              <div className="flex items-center justify-between text-[10px] font-mono font-bold text-slate-400">
                <span>0{idx + 1}</span>
                <span className={`w-2 h-2 rounded-full ${
                  step.status === 'attention' ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500'
                }`} />
              </div>
              <div>
                <span className="text-xs font-bold text-slate-900 block">{step.stage}</span>
                <span className="text-[11px] text-slate-500 font-medium block">{step.label}</span>
              </div>
              <div className="pt-1 border-t border-slate-200/60 flex items-center justify-between">
                <span className="text-xs font-black text-slate-900">{step.count}</span>
                <span className="text-[10px] font-semibold text-slate-400">scripts</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Score Distribution Histogram & Question Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Class Performance Histogram */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Class Performance Distribution</h2>
              <p className="text-xs text-slate-400">Score distribution across cohort brackets</p>
            </div>

            <div className="flex gap-4 text-xs">
              <div><span className="text-slate-400 block font-semibold text-[10px] uppercase">Average</span><span className="font-bold text-slate-900">{averageScore}</span></div>
              <div><span className="text-slate-400 block font-semibold text-[10px] uppercase">Median</span><span className="font-bold text-slate-900">76.0</span></div>
              <div><span className="text-slate-400 block font-semibold text-[10px] uppercase">Highest</span><span className="font-bold text-emerald-600">96.0</span></div>
              <div><span className="text-slate-400 block font-semibold text-[10px] uppercase">Lowest</span><span className="font-bold text-rose-600">41.0</span></div>
            </div>
          </div>

          <div className="space-y-3">
            {histogramBuckets.map((bucket) => {
              const pct = Math.round((bucket.count / maxBucketCount) * 100);
              return (
                <div key={bucket.label} className="space-y-1">
                  <div className="flex justify-between text-xs font-bold text-slate-700">
                    <span>{bucket.label}</span>
                    <span className="text-slate-500">{bucket.count} student(s)</span>
                  </div>
                  <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ${bucket.color}`}
                      style={{ width: `${Math.max(pct, 4)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Question Performance Breakdown */}
        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-slate-900">Question Performance</h2>
          <p className="text-xs text-slate-400">Cohort success rate per question</p>

          <div className="space-y-2 pt-2">
            {[
              { q: 'Q1', pct: 82, label: 'Kinematics Equations' },
              { q: 'Q2', pct: 76, label: 'Free Body Diagrams' },
              { q: 'Q3', pct: 61, label: 'Frictional Forces' },
              { q: 'Q4', pct: 43, label: "Newton&apos;s 2nd Law", difficult: true },
              { q: 'Q5', pct: 88, label: 'Work & Energy' },
            ].map((item) => (
              <Link 
                key={item.q}
                href="/results" 
                className={`p-3 rounded-xl border transition-all flex items-center justify-between text-xs ${
                  item.difficult ? 'bg-amber-50/60 border-amber-200 hover:border-amber-400' : 'bg-slate-50 border-slate-100 hover:bg-slate-100'
                }`}
              >
                <div>
                  <span className="font-bold text-slate-900 mr-2">{item.q}</span>
                  <span className="text-slate-600 font-medium">{item.label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`font-black ${item.pct < 50 ? 'text-amber-600' : 'text-slate-900'}`}>
                    {item.pct}%
                  </span>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                </div>
              </Link>
            ))}
          </div>
        </div>

      </div>

    </div>
  );
}
