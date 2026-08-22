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
import { 
  NumberTicker, 
  SpotlightCard, 
  ShimmerBadge, 
  BorderBeam,
  AnimatedList,
  AnimatedListItem,
  MagicBentoGrid,
  MagicBentoCard,
  PageHeroBanner
} from '@/components/ui';

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
      <div className="flex flex-col items-start justify-center min-h-[50vh] space-y-3">
        <div className="w-8 h-8 border-3 border-[#183B25] border-t-[#4A8B40] rounded-full animate-spin"></div>
        <p className="text-black font-extrabold text-xs">Loading Examination Workspace...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full max-w-xl text-left space-y-4 p-6 bg-white rounded-xl border-2 border-rose-300 shadow-xs">
        <div className="w-10 h-10 bg-rose-100 text-rose-700 rounded-lg flex items-center justify-center">
          <AlertCircle className="w-5 h-5" />
        </div>
        <div>
          <h2 className="text-sm font-black text-black">Workspace Connection Alert</h2>
          <p className="text-black text-xs font-bold mt-1">{error}</p>
        </div>
        <button 
          onClick={() => window.location.reload()} 
          className="px-4 py-2 bg-[#183B25] text-white font-black text-xs rounded-lg hover:bg-forest-800 transition-colors"
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
    { stage: 'LAYOUT', label: 'Layout & Rubric', count: Math.max(totalSubmissions - 1, 0), status: 'complete' },
    { stage: 'EVALUATE', label: 'AI Evaluation', count: evaluatedSubmissions, status: 'active' },
    { stage: 'REVIEW', label: 'Human Review', count: needsReviewCount, status: needsReviewCount > 0 ? 'attention' : 'complete' },
    { stage: 'REPORT', label: 'Reports Issued', count: evaluatedSubmissions, status: 'complete' },
  ];

  // Distribution Data
  const scoreDist = monitoring?.score_distribution || { "90-100": 8, "80-89": 10, "70-79": 4, "60-69": 2, "below_60": 0 };
  const histogramBuckets = [
    { label: '90-100%', count: scoreDist['90-100'] || 0, color: 'bg-[#183B25]' },
    { label: '80-89%', count: scoreDist['80-89'] || 0, color: 'bg-[#2D5A38]' },
    { label: '70-79%', count: scoreDist['70-79'] || 0, color: 'bg-[#4A8B40]' },
    { label: '60-69%', count: scoreDist['60-69'] || 0, color: 'bg-amber-600' },
    { label: '<60%', count: scoreDist.below_60 || 0, color: 'bg-rose-600' },
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
    <div className="flex-1 flex flex-col justify-between space-y-6 text-left w-full text-black">
      
      {/* 1. Elevated Reference Picture Hero Banner */}
      <PageHeroBanner
        badgeLabel="FACULTY LEAD WORKSPACE"
        badgeIcon={<Sparkles className="w-3.5 h-3.5 text-emerald-400" />}
        title="Dashboard Overview"
        subtitle="Real-time assessment tracking, AI evaluation pipeline, and cohort performance analytics."
        statLabel="SUBMISSIONS"
        statValue={`${totalSubmissions} Submissions`}
        actionButton={
          <div className="flex items-center gap-3">
            <Link
              href="/upload"
              className="px-4 py-2.5 bg-[#4A8B40] hover:bg-[#3B7233] text-white font-black text-xs rounded-xl transition-all flex items-center gap-1.5 shadow-md group"
            >
              <Plus className="w-4 h-4 text-white group-hover:rotate-90 transition-transform duration-300" /> Create Assessment
            </Link>
            <Link
              href="/upload"
              className="px-4 py-2.5 bg-white/10 hover:bg-white/20 text-white font-black text-xs rounded-xl border border-white/20 transition-all flex items-center gap-1.5 group"
            >
              <UploadCloud className="w-4 h-4 text-emerald-400 group-hover:-translate-y-1 transition-transform duration-300" /> Upload Sheets
            </Link>
          </div>
        }
      />

      {/* 2. Unified Magic Bento KPI Section */}
      <MagicBentoCard colSpan="col-span-4" className="p-0 overflow-hidden bg-white border-2 border-emerald-800/30 shadow-md">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-emerald-800/20">
          
          <div className="p-5 md:p-6 space-y-1">
            <span className="text-[11px] font-black text-black uppercase tracking-wider block">
              Total Submissions
            </span>
            <div className="text-3xl font-serif font-black text-[#183B25] tracking-tight">
              <NumberTicker value={totalSubmissions} />
            </div>
            <p className="text-xs text-black font-bold">
              Out of {activeExam.total_students || 30} enrolled students
            </p>
          </div>

          <div className="p-5 md:p-6 space-y-1">
            <span className="text-[11px] font-black text-black uppercase tracking-wider block">
              Evaluated Scripts
            </span>
            <div className="text-3xl font-serif font-black text-[#183B25] tracking-tight">
              <NumberTicker value={evaluatedSubmissions} />
            </div>
            <p className="text-xs text-black font-bold">
              {Math.round((evaluatedSubmissions / Math.max(totalSubmissions, 1)) * 100)}% autonomous AI evaluation rate
            </p>
          </div>

          <div className="p-5 md:p-6 space-y-1">
            <span className="text-[11px] font-black text-black uppercase tracking-wider block">
              Human Review Queue
            </span>
            <div className="text-3xl font-serif font-black text-amber-800 tracking-tight">
              <NumberTicker value={needsReviewCount} className="text-amber-800" />
            </div>
            <p className="text-xs text-amber-900 font-extrabold">
              Requires faculty verification
            </p>
          </div>

          <div className="p-5 md:p-6 space-y-1">
            <span className="text-[11px] font-black text-black uppercase tracking-wider block">
              Class Average Score
            </span>
            <div className="text-3xl font-serif font-black text-[#183B25] tracking-tight">
              <NumberTicker value={averageScore} decimalPlaces={1} suffix="%" />
            </div>
            <p className="text-xs text-[#183B25] font-black">
              +3.4% vs previous unit test
            </p>
          </div>

        </div>
      </MagicBentoCard>

      {/* 3. Primary Content Row - ReactBits Magic Bento Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 md:gap-8 items-start">
        
        {/* Main Chart Column (8 cols ~66%) */}
        <MagicBentoCard colSpan="lg:col-span-8" className="p-6 space-y-6 border-2 border-emerald-800/30">
          
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b-2 border-emerald-800/10 pb-4 gap-4">
            <div>
              <h2 className="text-lg font-serif font-black text-black tracking-tight">
                Class Performance Distribution
              </h2>
              <p className="text-xs text-black font-bold">
                Cohort score breakdown across grade percentage brackets
              </p>
            </div>

            <div className="flex gap-4 text-xs shrink-0">
              <div>
                <span className="text-black block font-black text-[10px] uppercase">Average</span>
                <span className="font-serif font-black text-black text-sm">{averageScore}%</span>
              </div>
              <div>
                <span className="text-black block font-black text-[10px] uppercase">Median</span>
                <span className="font-serif font-black text-black text-sm">76.0%</span>
              </div>
              <div>
                <span className="text-black block font-black text-[10px] uppercase">Highest</span>
                <span className="font-serif font-black text-[#183B25] text-sm">96.0%</span>
              </div>
              <div>
                <span className="text-black block font-black text-[10px] uppercase">Lowest</span>
                <span className="font-serif font-black text-rose-800 text-sm">41.0%</span>
              </div>
            </div>
          </div>

          {/* Histogram Content */}
          <div className="space-y-4 pt-1">
            {histogramBuckets.map((bucket) => {
              const pct = Math.round((bucket.count / maxBucketCount) * 100);
              return (
                <div key={bucket.label} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-black text-black">
                    <span>{bucket.label}</span>
                    <span className="text-black font-bold">{bucket.count} student(s)</span>
                  </div>
                  <div className="w-full h-3 bg-emerald-100/60 rounded-lg overflow-hidden border border-emerald-300">
                    <div 
                      className={`h-full rounded-lg transition-all duration-500 ${bucket.color}`}
                      style={{ width: `${Math.max(pct, 4)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Assessment Progress Footer Strip */}
          <div className="pt-4 border-t-2 border-emerald-800/10 grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-black text-black">
                <span>Submission Intake Progress</span>
                <span className="text-black">{activeExam.submission_count || totalSubmissions} / {activeExam.total_students || 30}</span>
              </div>
              <div className="w-full h-2.5 bg-emerald-100 rounded-full overflow-hidden border border-emerald-300">
                <div 
                  className="h-full bg-[#183B25] rounded-full" 
                  style={{ width: `${Math.round(((activeExam.submission_count || totalSubmissions) / 30) * 100)}%` }} 
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-black text-black">
                <span>AI Evaluation Progress</span>
                <span className="text-[#183B25] font-extrabold">{evaluatedSubmissions} evaluated</span>
              </div>
              <div className="w-full h-2.5 bg-emerald-100 rounded-full overflow-hidden border border-emerald-300">
                <div 
                  className="h-full bg-[#4A8B40] rounded-full" 
                  style={{ width: `${Math.round((evaluatedSubmissions / Math.max(totalSubmissions, 1)) * 100)}%` }} 
                />
              </div>
            </div>
          </div>

        </MagicBentoCard>

        {/* Action Panel Column (4 cols ~34%) */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Action Required Panel */}
          <MagicBentoCard showBeam={needsReviewCount > 0} beamColorFrom="#4A8B40" beamColorTo="#183B25" className="p-6 space-y-4 border-2 border-emerald-800/30">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-black text-black uppercase tracking-wider flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-700" /> Action Required Right Now
              </h2>
              <ShimmerBadge variant="amber">
                {needsReviewCount} Pending
              </ShimmerBadge>
            </div>

            {needsReviewCount > 0 ? (
              <div className="p-4 rounded-xl bg-amber-50 border-2 border-amber-300 space-y-3">
                <div>
                  <h3 className="text-sm font-black text-black">{activeExam.title}</h3>
                  <p className="text-xs text-black font-bold mt-1">
                    {evaluatedSubmissions} evaluated automatically. <span className="font-black text-amber-900">{needsReviewCount} answer scripts flagged for human review</span> due to confidence threshold.
                  </p>
                </div>
                <Link
                  href="/review"
                  className="inline-flex items-center gap-1 px-4 py-2 bg-amber-800 hover:bg-amber-900 text-white font-black text-xs rounded-xl transition-colors shadow-xs"
                >
                  Review {needsReviewCount} Answers →
                </Link>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-emerald-50 border-2 border-emerald-300 flex items-center gap-2.5 text-black text-xs font-black">
                <CheckCircle2 className="w-4 h-4 text-[#183B25] shrink-0" />
                <span>Everything is up to date. All scripts passed confidence thresholds.</span>
              </div>
            )}
          </MagicBentoCard>

          {/* Assessment Intelligence Insights */}
          <MagicBentoCard className="p-6 space-y-4 border-2 border-emerald-800/30">
            <h2 className="text-xs font-black text-black uppercase tracking-wider flex items-center gap-1.5">
              <Brain className="w-4 h-4 text-[#183B25]" /> Assessment Intelligence
            </h2>

            <div className="space-y-3 divide-y-2 divide-emerald-800/10">
              <div className="pt-2 first:pt-0 space-y-1">
                <span className="text-[10px] font-black text-black uppercase tracking-wider block">
                  Weakest Concept Mastery
                </span>
                <h3 className="text-xs font-black text-black">Newton&apos;s Second Law</h3>
                <p className="text-xs text-rose-800 font-black">42% student mastery rate across cohort</p>
              </div>

              <div className="pt-3 space-y-1">
                <span className="text-[10px] font-black text-black uppercase tracking-wider block">
                  Most Common Error
                </span>
                <h3 className="text-xs font-black text-black">Confusing mass with acceleration</h3>
                <p className="text-xs text-black font-bold">Identified in 31% of student answers</p>
              </div>

              <div className="pt-3 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-black text-black uppercase tracking-wider block">
                    AI Evaluation Confidence
                  </span>
                  <span className="text-base font-serif font-black text-[#183B25]">
                    <NumberTicker value={averageConfidence} suffix="%" />
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-black text-black uppercase tracking-wider block">
                    Human Review Ratio
                  </span>
                  <span className="text-xs font-black text-black">{needsReviewCount} / {totalSubmissions}</span>
                </div>
              </div>
            </div>
          </MagicBentoCard>

        </div>

      </div>

      {/* 4. Lower Content Row - ReactBits AnimatedList inside MagicBentoGrid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 items-stretch">
        
        {/* Column 1: Evaluation Lifecycle Pipeline */}
        <MagicBentoCard className="p-6 space-y-4 flex flex-col justify-between border-2 border-emerald-800/30">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-base font-serif font-black text-black">Evaluation Pipeline</h2>
              <ShimmerBadge variant="emerald">Operational</ShimmerBadge>
            </div>
            <p className="text-xs text-black font-bold mb-4">
              Real-time script processing lifecycle
            </p>

            <AnimatedList delay={300}>
              {pipeline.map((step, idx) => (
                <div key={step.stage} className="p-2.5 rounded-xl bg-emerald-50 border-2 border-emerald-200 flex items-center justify-between text-xs transition-colors hover:bg-emerald-100/80 w-full">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-[10px] font-black text-[#183B25]">0{idx + 1}</span>
                    <span className={`w-2.5 h-2.5 rounded-full ${step.status === 'attention' ? 'bg-amber-600' : 'bg-[#183B25]'}`} />
                    <span className="font-black text-black">{step.label}</span>
                  </div>
                  <span className="font-black text-black">{step.count} <span className="text-[10px] font-bold text-black">scripts</span></span>
                </div>
              ))}
            </AnimatedList>
          </div>
        </MagicBentoCard>

        {/* Column 2: Question Performance Breakdown */}
        <MagicBentoCard className="p-6 space-y-4 flex flex-col justify-between border-2 border-emerald-800/30">
          <div>
            <h2 className="text-base font-serif font-black text-black mb-1">Question Performance</h2>
            <p className="text-xs text-black font-bold mb-4">
              Cohort success rate per question item
            </p>

            <AnimatedList delay={350}>
              {[
                { q: 'Q1', pct: 82, label: 'Kinematics Equations' },
                { q: 'Q2', pct: 76, label: 'Free Body Diagrams' },
                { q: 'Q3', pct: 61, label: 'Frictional Forces' },
                { q: 'Q4', pct: 43, label: "Newton's 2nd Law", difficult: true },
                { q: 'Q5', pct: 88, label: 'Work & Energy' },
              ].map((item) => (
                <Link 
                  key={item.q}
                  href="/results" 
                  className={`p-2.5 rounded-xl border-2 transition-all flex items-center justify-between text-xs w-full ${
                    item.difficult 
                      ? 'bg-amber-50 border-amber-300 hover:border-amber-400' 
                      : 'bg-emerald-50 border-emerald-200 hover:bg-emerald-100/80'
                  }`}
                >
                  <div>
                    <span className="font-black text-black mr-2">{item.q}</span>
                    <span className="text-black font-bold">{item.label}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`font-black ${item.pct < 50 ? 'text-amber-900' : 'text-black'}`}>
                      {item.pct}%
                    </span>
                    <ChevronRight className="w-4 h-4 text-[#183B25]" />
                  </div>
                </Link>
              ))}
            </AnimatedList>
          </div>
        </MagicBentoCard>

        {/* Column 3: Active Assessment & System Status */}
        <MagicBentoCard className="p-6 space-y-4 flex flex-col justify-between border-2 border-emerald-800/30">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-base font-serif font-black text-black">Active Assessment Details</h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-black bg-[#183B25] text-white">
                {activeExam.class_name || 'Class 12-A'}
              </span>
            </div>
            <p className="text-xs text-black font-bold mb-4">
              Current active evaluation workspace session
            </p>

            <div className="p-4 rounded-xl bg-emerald-50 border-2 border-emerald-200 space-y-3 text-xs">
              <div>
                <span className="text-[10px] font-black text-black uppercase tracking-wider block">Assessment Title</span>
                <span className="font-black text-black">{activeExam.title}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-emerald-300">
                <div>
                  <span className="text-[10px] font-black text-black uppercase tracking-wider block">Enrolled Students</span>
                  <span className="font-black text-black">{activeExam.total_students || 30}</span>
                </div>
                <div>
                  <span className="text-[10px] font-black text-black uppercase tracking-wider block">Submissions Received</span>
                  <span className="font-black text-black">{activeExam.submission_count || totalSubmissions}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-emerald-300">
                <div>
                  <span className="text-[10px] font-black text-black uppercase tracking-wider block">AI Evaluated</span>
                  <span className="font-black text-[#183B25]">{evaluatedSubmissions}</span>
                </div>
                <div>
                  <span className="text-[10px] font-black text-black uppercase tracking-wider block">Needs Review</span>
                  <span className="font-black text-amber-900">{needsReviewCount}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t-2 border-emerald-800/10 flex items-center justify-between">
            <span className="text-[11px] text-black font-bold">Last activity: 4m ago</span>
            <Link
              href="/results"
              className="text-xs font-black text-[#183B25] hover:text-[#4A8B40] flex items-center gap-1 transition-colors"
            >
              Open Results Workspace <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </MagicBentoCard>

      </div>

    </div>
  );
}
