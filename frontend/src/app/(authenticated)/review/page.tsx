'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  ArrowRight, 
  FileText, 
  Search, 
  Filter, 
  Eye, 
  UserCheck, 
  Edit3, 
  Sparkles,
  HelpCircle
} from 'lucide-react';
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

export default function ReviewQueuePage() {
  const router = useRouter();
  const [submissions, setSubmissions] = useState<SubmissionItem[]>([]);
  const [examsMap, setExamsMap] = useState<Record<string, { title: string; subject: string }>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'needs_review' | 'verified'>('all');
  const [reviewedIds, setReviewedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [subRes, examsRes] = await Promise.all([
          SubmissionService.getSubmissions({ limit: 50 }),
          ExamService.getExams()
        ]);

        const mapping: Record<string, { title: string; subject: string }> = {};
        if (examsRes.success && Array.isArray(examsRes.data)) {
          examsRes.data.forEach((exam: any) => {
            mapping[exam.id] = { title: exam.title, subject: exam.subject };
          });
          setExamsMap(mapping);
        }

        if (subRes.success && subRes.data) {
          const list = Array.isArray(subRes.data.submissions) 
            ? subRes.data.submissions 
            : (Array.isArray(subRes.data) ? subRes.data : []);
          setSubmissions(list);
        }
      } catch (err: any) {
        console.error('Failed to load review queue:', err);
        setError('Could not load review queue submissions.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const handleAcceptScore = (id: string) => {
    setReviewedIds(prev => new Set(prev).add(id));
  };

  const filteredSubmissions = submissions.filter(sub => {
    const examInfo = examsMap[sub.exam_id] || { title: '', subject: '' };
    const matchesSearch = 
      sub.student_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sub.student_roll_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
      examInfo.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      examInfo.subject.toLowerCase().includes(searchQuery.toLowerCase());

    const confidence = sub.evaluation_confidence ?? 0.85;
    const isNeedsReview = confidence < 0.85 || sub.status !== 'COMPLETED';

    if (statusFilter === 'needs_review') return matchesSearch && isNeedsReview;
    if (statusFilter === 'verified') return matchesSearch && !isNeedsReview;
    return matchesSearch;
  });

  return (
    <div className="flex-1 flex flex-col space-y-5 text-left w-full">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-forest-200 pb-5">
        <div>
          <div className="inline-flex items-center gap-1.5 text-xs font-bold text-forest-600 uppercase tracking-wider mb-1">
            Human-in-the-Loop Oversight
          </div>
          <h1 className="text-2xl font-serif font-extrabold text-forest-900 tracking-tight">Review Queue</h1>
          <p className="text-xs text-forest-600 mt-0.5">
            Audit AI evaluation scores, verify student answers, and approve final marks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="px-4 py-2 bg-white hover:bg-forest-50 text-forest-900 font-bold text-xs rounded-xl border border-forest-200 transition-colors shadow-2xs"
          >
            ← Examination Workspace
          </Link>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
          <input 
            type="text" 
            placeholder="Search student, roll number, or subject..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-slate-400" />
          <div className="flex bg-slate-100 p-1 rounded-xl text-xs font-bold">
            <button 
              onClick={() => setStatusFilter('all')}
              className={`px-3 py-1.5 rounded-lg transition-all ${statusFilter === 'all' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'}`}
            >
              All Submissions
            </button>
            <button 
              onClick={() => setStatusFilter('needs_review')}
              className={`px-3 py-1.5 rounded-lg transition-all ${statusFilter === 'needs_review' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'}`}
            >
              Needs Review
            </button>
            <button 
              onClick={() => setStatusFilter('verified')}
              className={`px-3 py-1.5 rounded-lg transition-all ${statusFilter === 'verified' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'}`}
            >
              Verified High Confidence
            </button>
          </div>
        </div>
      </div>

      {/* Submissions Queue Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-slate-500 font-bold text-xs animate-pulse">
            Loading Review Queue...
          </div>
        ) : filteredSubmissions.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900">Review Queue Empty</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              All submitted student answers have been evaluated with high confidence or approved by faculty.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-6">Student & Roll No.</th>
                  <th className="py-3 px-6">Assessment & Subject</th>
                  <th className="py-3 px-6 text-center">AI Score</th>
                  <th className="py-3 px-6 text-center">Evaluation Confidence</th>
                  <th className="py-3 px-6">Status / Reason</th>
                  <th className="py-3 px-6 text-right">Human Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {filteredSubmissions.map((sub) => {
                  const examInfo = examsMap[sub.exam_id] || { title: 'Assessment', subject: 'General' };
                  const isApproved = reviewedIds.has(sub.id);
                  const confidencePct = Math.round((sub.evaluation_confidence ?? 0.88) * 100);
                  const needsReview = confidencePct < 85 && !isApproved;

                  return (
                    <tr key={sub.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-4 px-6">
                        <div className="font-bold text-slate-900">{sub.student_name}</div>
                        <div className="text-[11px] font-mono text-slate-400">{sub.student_roll_number || 'N/A'}</div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="font-bold text-slate-700">{examInfo.title}</div>
                        <div className="text-[11px] text-slate-400">{examInfo.subject}</div>
                      </td>
                      <td className="py-4 px-6 text-center font-black text-slate-900 text-sm">
                        {sub.obtained_marks !== undefined && sub.total_marks
                          ? `${sub.obtained_marks} / ${sub.total_marks}`
                          : '--'}
                      </td>
                      <td className="py-4 px-6 text-center">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full font-bold text-[10px] ${
                          confidencePct >= 85
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}>
                          {confidencePct}%
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        {isApproved ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                            <UserCheck className="w-3 h-3" /> Teacher Approved
                          </span>
                        ) : needsReview ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                            <AlertCircle className="w-3 h-3" /> Review Recommended
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" /> High Confidence
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-6 text-right space-x-2">
                        {!isApproved && (
                          <button 
                            onClick={() => handleAcceptScore(sub.id)}
                            className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-[11px] rounded-lg transition-colors"
                          >
                            Accept Score
                          </button>
                        )}
                        <button 
                          onClick={() => router.push(`/results?submissionId=${sub.id}`)}
                          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-[11px] rounded-lg transition-colors border border-slate-200"
                        >
                          Audit Details →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
