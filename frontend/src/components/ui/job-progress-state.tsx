"use client";

import React, { useState, useEffect } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  RefreshCw,
  Database,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Zap,
  Cpu,
  FileText,
  UserCheck
} from "lucide-react";
import { Button } from "@/components/ui/button";

export interface PageStateData {
  page_number: number;
  page_sha256: string;
  status: "PENDING" | "CACHED" | "TRANSCRIBED" | "FAILED";
  error?: string | null;
  attempts: number;
  completed_at?: string | null;
}

export interface QuestionStateData {
  question_number: string;
  status: "SCORED" | "ROUTED" | "NO_SCHEME" | "PENDING_TRANSCRIPTION";
  mark?: number | null;
  max_marks?: number | null;
  blocked_by_page?: number | null;
  human_reviewed?: boolean;
  human_mark?: number | null;
  reason_code?: string | null;
  reviewed_at?: string | null;
}

export interface EventItemData {
  timestamp: string;
  event: string;
  detail: string;
}

export interface JobMetricsData {
  pages_reused_from_cache: number;
  pages_transcribed_this_run: number;
  api_calls_made: number;
  summary: string;
}

export interface JobStateData {
  job_id: string;
  created_at: string;
  updated_at: string;
  status: "RUNNING" | "COMPLETE" | "PARTIAL" | "FAILED";
  pages: PageStateData[];
  questions: QuestionStateData[];
  events: EventItemData[];
  error?: string | null;
  input_hash?: string | null;
  metrics?: JobMetricsData;
}

interface JobProgressStateProps {
  jobId: string;
  initialData?: JobStateData | null;
  onResumed?: () => void;
}

export function JobProgressState({ jobId, initialData, onResumed }: JobProgressStateProps) {
  const [data, setData] = useState<JobStateData | null>(initialData || null);
  const [loading, setLoading] = useState<boolean>(!initialData);
  const [resuming, setResuming] = useState<boolean>(false);
  const [showEvents, setShowEvents] = useState<boolean>(false);

  const fetchState = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/v2/grade/${jobId}`);
      if (res.ok) {
        const json = await res.json();
        setData(json.state || json);
      }
    } catch (e) {
      console.error("Failed to fetch job state:", e);
    } finally {
      setLoading(false);
    }
  };

  const rawStatus = (data?.status || "").toUpperCase();
  const normalizedStatus: "COMPLETE" | "PARTIAL" | "FAILED" | "RUNNING" =
    rawStatus === "COMPLETED" || rawStatus === "COMPLETE"
      ? "COMPLETE"
      : rawStatus === "FAILED"
      ? "FAILED"
      : rawStatus === "PARTIAL"
      ? "PARTIAL"
      : "RUNNING";

  useEffect(() => {
    if (!jobId) return;
    
    fetchState();

    const interval = setInterval(() => {
      if (!data || normalizedStatus === "RUNNING") {
        fetchState();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, normalizedStatus]);

  const handleResume = async () => {
    try {
      setResuming(true);
      const res = await fetch(`http://localhost:8000/api/v2/grade/${jobId}/resume`, {
        method: "POST"
      });
      if (res.ok) {
        await fetchState();
        if (onResumed) onResumed();
      }
    } catch (e) {
      console.error("Failed to resume job:", e);
    } finally {
      setResuming(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="p-6 rounded-2xl bg-[#183B25] border-2 border-[#4A8B40] flex items-center gap-3 text-white shadow-lg">
        <RefreshCw className="w-5 h-5 animate-spin text-emerald-400" />
        <span className="font-bold text-sm">Loading job evaluation state...</span>
      </div>
    );
  }

  if (!data) return null;

  const statusColors = {
    COMPLETE: "bg-[#183B25] text-white border-2 border-emerald-500",
    PARTIAL: "bg-amber-950 text-white border-2 border-amber-500",
    FAILED: "bg-rose-950 text-white border-2 border-rose-500",
    RUNNING: "bg-[#183B25] text-white border-2 border-emerald-400 animate-pulse"
  };

  const statusIcons = {
    COMPLETE: <CheckCircle2 className="w-6 h-6 text-emerald-400" />,
    PARTIAL: <AlertTriangle className="w-6 h-6 text-amber-400" />,
    FAILED: <XCircle className="w-6 h-6 text-rose-400" />,
    RUNNING: <RefreshCw className="w-6 h-6 text-emerald-400 animate-spin" />
  };

  const pagesList = data.pages || [];
  const questionsList = data.questions || [];
  const eventsList = data.events || [];

  const reusedCount = data.metrics?.pages_reused_from_cache ?? pagesList.filter(p => p.status === "CACHED").length;
  const apiCallsCount = data.metrics?.api_calls_made ?? pagesList.filter(p => p.status === "TRANSCRIBED").reduce((acc, p) => acc + (p.attempts || 1), 0);

  return (
    <div className="space-y-6">
      {/* 1. Status Banner & Actions Header */}
      <div className={`p-5 rounded-2xl border-2 ${statusColors[normalizedStatus]} flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl`}>
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-xl bg-black/40 border border-white/20">
            {statusIcons[normalizedStatus]}
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <span className="font-black text-xl tracking-wider uppercase text-white">{normalizedStatus} JOB STATE</span>
              <span className="text-xs px-3 py-1 rounded-full bg-black/40 text-emerald-300 font-mono font-black border border-emerald-400/40">
                ID: {data.job_id ? data.job_id.slice(0, 8) : jobId.slice(0, 8)}
              </span>
            </div>
            <p className="text-xs font-semibold text-emerald-100/90 mt-1">
              Updated {data.updated_at ? new Date(data.updated_at).toLocaleTimeString() : new Date().toLocaleTimeString()} • {pagesList.length} page(s) • {questionsList.length} question(s)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 ml-auto">
          {normalizedStatus === "COMPLETE" && (
            <a
              href={`/results?job_id=${data.job_id || jobId}`}
              className="px-6 py-3 bg-[#4A8B40] hover:bg-[#3D7434] text-white font-black text-xs md:text-sm rounded-xl transition-all shadow-lg flex items-center gap-2 border-2 border-emerald-400 cursor-pointer animate-bounce"
            >
              <span>View Evaluation Results</span>
              <Zap className="w-4 h-4 text-emerald-200" />
            </a>
          )}

          {(normalizedStatus === "PARTIAL" || normalizedStatus === "FAILED") && (
            <Button
              onClick={handleResume}
              disabled={resuming}
              className="bg-[#4A8B40] hover:bg-[#3D7434] text-white font-black shadow-lg transition-all duration-200 hover:-translate-y-0.5 flex items-center gap-2 px-6 py-3 rounded-xl border-2 border-emerald-400 cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${resuming ? "animate-spin" : ""}`} />
              {resuming ? "Resuming Evaluation..." : "Resume Evaluation"}
            </Button>
          )}
        </div>
      </div>

      {/* 2. Cache Savings Proof Banner */}
      <div className="p-5 rounded-2xl bg-[#183B25] border-2 border-[#4A8B40] text-white flex flex-wrap items-center justify-between gap-4 shadow-lg">
        <div className="flex items-center gap-3.5">
          <div className="p-2.5 rounded-xl bg-emerald-500/20 border border-emerald-400/40 text-emerald-300">
            <Zap className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <div className="text-sm font-black text-white flex items-center gap-2.5">
              Progress Preservation Active
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-400/20 text-emerald-200 font-mono font-bold border border-emerald-400/40">
                {apiCallsCount} API calls • {reusedCount} pages reused
              </span>
            </div>
            <p className="text-xs text-emerald-100/90 font-semibold mt-0.5">
              Work paid for is cached on disk. Re-runs skip HTR calls and preserve marks.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-white">
          <div className="flex items-center gap-2 bg-black/40 px-3.5 py-1.5 rounded-xl border border-emerald-400/40">
            <Database className="w-4 h-4 text-emerald-400" />
            <span>Cache Reused: <strong className="text-emerald-300 font-black">{reusedCount}</strong></span>
          </div>
          <div className="flex items-center gap-2 bg-black/40 px-3.5 py-1.5 rounded-xl border border-amber-400/40">
            <Cpu className="w-4 h-4 text-amber-400" />
            <span>API Calls: <strong className="text-amber-300 font-black">{apiCallsCount}</strong></span>
          </div>
        </div>
      </div>

      {/* 3. Page Grid & Question Table Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Page Status Card */}
        <div className="p-5 rounded-2xl bg-white border-2 border-emerald-800/20 shadow-md">
          <h3 className="text-sm font-black text-[#183B25] mb-3.5 flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#4A8B40]" />
            Per-Page HTR Status
          </h3>
          <div className="space-y-2.5">
            {pagesList.map((p) => (
              <div
                key={p.page_number}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs hover:border-emerald-300 transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <span className="w-7 h-7 rounded-lg bg-[#183B25] text-white font-black flex items-center justify-center font-mono text-xs shadow-sm">
                    {p.page_number}
                  </span>
                  <span className="font-mono text-slate-700 font-bold">
                    sha256: {p.page_sha256?.slice(0, 12)}...
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-md font-black font-mono text-[11px] uppercase tracking-wider ${
                      p.status === "CACHED"
                        ? "bg-emerald-100 text-emerald-900 border border-emerald-400"
                        : p.status === "TRANSCRIBED"
                        ? "bg-blue-100 text-blue-900 border border-blue-400"
                        : p.status === "FAILED"
                        ? "bg-rose-100 text-rose-900 border border-rose-400"
                        : "bg-slate-200 text-slate-800 border border-slate-400"
                    }`}
                  >
                    {p.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Questions Status Card */}
        <div className="p-5 rounded-2xl bg-white border-2 border-emerald-800/20 shadow-md">
          <h3 className="text-sm font-black text-[#183B25] mb-3.5 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#4A8B40]" />
            Question Evaluation & Human Reviews
          </h3>
          <div className="max-h-[260px] overflow-y-auto pr-1 space-y-2.5">
            {questionsList.map((q) => (
              <div
                key={q.question_number}
                className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs hover:border-emerald-300 transition-colors"
              >
                <div className="flex items-center gap-2.5">
                  <span className="font-black text-[#183B25] font-mono text-sm w-10">
                    Q{q.question_number}
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded text-[11px] font-mono font-black ${
                      q.status === "SCORED"
                        ? "bg-emerald-100 text-emerald-900 border border-emerald-400"
                        : q.status === "ROUTED"
                        ? "bg-amber-100 text-amber-900 border border-amber-400"
                        : q.status === "NO_SCHEME"
                        ? "bg-slate-200 text-slate-800 border border-slate-400"
                        : "bg-rose-100 text-rose-900 border border-rose-400"
                    }`}
                  >
                    {q.status}
                  </span>
                  {q.human_reviewed && (
                    <span className="flex items-center gap-1 px-2.5 py-0.5 rounded bg-indigo-100 text-indigo-900 text-[10px] font-bold border border-indigo-300">
                      <UserCheck className="w-3 h-3 text-indigo-700" />
                      {q.reason_code || "REVIEWED"}
                    </span>
                  )}
                </div>

                <div className="font-mono text-[#183B25] font-black text-sm">
                  {q.human_reviewed && q.human_mark !== null
                    ? `${q.human_mark} / ${q.max_marks ?? "?"} (Human)`
                    : q.mark !== null
                    ? `${q.mark} / ${q.max_marks ?? "?"}`
                    : "—"}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. Collapsible Event History Timeline */}
      <div className="rounded-2xl bg-white border-2 border-emerald-800/20 shadow-md overflow-hidden">
        <button
          onClick={() => setShowEvents(!showEvents)}
          className="w-full p-4 bg-emerald-50/80 flex items-center justify-between text-xs font-black text-[#183B25] hover:bg-emerald-100/80 transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#4A8B40]" />
            Chronological Job History ({eventsList.length} events logged)
          </div>
          {showEvents ? <ChevronUp className="w-4 h-4 text-[#183B25]" /> : <ChevronDown className="w-4 h-4 text-[#183B25]" />}
        </button>

        {showEvents && (
          <div className="p-4 max-h-[300px] overflow-y-auto space-y-2.5 font-mono text-[11px] bg-slate-50">
            {eventsList.map((evt, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-xl bg-white border border-slate-200 flex items-start gap-3 shadow-sm"
              >
                <span className="text-slate-500 font-bold whitespace-nowrap">
                  {new Date(evt.timestamp).toLocaleTimeString()}
                </span>
                <span className="font-black text-[#183B25] uppercase min-w-[130px]">
                  {evt.event}
                </span>
                <span className="text-slate-800 font-medium">{evt.detail}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
