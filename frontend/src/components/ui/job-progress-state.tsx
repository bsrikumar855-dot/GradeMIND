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
      setLoading(true);
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

  useEffect(() => {
    if (!initialData && jobId) {
      fetchState();
    }
  }, [jobId]);

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
      <div className="p-6 rounded-xl bg-[#183B25]/40 border border-[#4A8B40]/30 flex items-center gap-3 text-emerald-200">
        <RefreshCw className="w-5 h-5 animate-spin text-[#4A8B40]" />
        <span>Loading job progress state...</span>
      </div>
    );
  }

  if (!data) return null;

  const statusColors = {
    COMPLETE: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    PARTIAL: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    FAILED: "bg-rose-500/15 text-rose-400 border-rose-500/30",
    RUNNING: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30 animate-pulse"
  };

  const statusIcons = {
    COMPLETE: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
    PARTIAL: <AlertTriangle className="w-5 h-5 text-amber-400" />,
    FAILED: <XCircle className="w-5 h-5 text-rose-400" />,
    RUNNING: <RefreshCw className="w-5 h-5 text-emerald-400 animate-spin" />
  };

  const reusedCount = data.metrics?.pages_reused_from_cache ?? data.pages.filter(p => p.status === "CACHED").length;
  const apiCallsCount = data.metrics?.api_calls_made ?? data.pages.filter(p => p.status === "TRANSCRIBED").reduce((acc, p) => acc + (p.attempts || 1), 0);

  return (
    <div className="space-y-6">
      {/* 1. Status Banner & Resume Header */}
      <div className={`p-5 rounded-2xl border ${statusColors[data.status] || statusColors.RUNNING} flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-lg backdrop-blur-md`}>
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-black/20 backdrop-blur-sm">
            {statusIcons[data.status] || statusIcons.RUNNING}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-wide uppercase">{data.status} JOB STATE</span>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-black/30 text-emerald-300/80 font-mono">
                ID: {data.job_id.slice(0, 8)}
              </span>
            </div>
            <p className="text-xs opacity-80 mt-0.5">
              Updated {new Date(data.updated_at).toLocaleTimeString()} • {data.pages.length} page(s) • {data.questions.length} question(s)
            </p>
          </div>
        </div>

        {(data.status === "PARTIAL" || data.status === "FAILED") && (
          <Button
            onClick={handleResume}
            disabled={resuming}
            className="bg-[#4A8B40] hover:bg-[#3D7434] text-white font-medium shadow-md transition-all duration-200 hover:-translate-y-0.5 flex items-center gap-2 px-5 py-2.5 rounded-xl ml-auto"
          >
            <RefreshCw className={`w-4 h-4 ${resuming ? "animate-spin" : ""}`} />
            {resuming ? "Resuming Evaluation..." : "Resume Evaluation"}
          </Button>
        )}
      </div>

      {/* 2. Cache Savings Proof Banner */}
      <div className="p-4 rounded-xl bg-[#183B25]/60 border border-[#4A8B40]/30 text-emerald-200 flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[#4A8B40]/20 text-[#4A8B40]">
            <Zap className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <div className="text-sm font-semibold text-white flex items-center gap-2">
              Progress Preservation Active
              <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono">
                {apiCallsCount} API calls • {reusedCount} pages reused
              </span>
            </div>
            <p className="text-xs text-emerald-300/70">
              Work paid for is cached on disk. Re-runs skip HTR calls and preserve marks.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-emerald-200/90">
          <div className="flex items-center gap-1.5 bg-black/20 px-3 py-1.5 rounded-lg border border-[#4A8B40]/20">
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span>Cache Reused: <strong>{reusedCount}</strong></span>
          </div>
          <div className="flex items-center gap-1.5 bg-black/20 px-3 py-1.5 rounded-lg border border-[#4A8B40]/20">
            <Cpu className="w-3.5 h-3.5 text-amber-400" />
            <span>API Calls: <strong>{apiCallsCount}</strong></span>
          </div>
        </div>
      </div>

      {/* 3. Page Grid & Question Table Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Page Status Card */}
        <div className="p-5 rounded-2xl bg-[#183B25]/40 border border-[#4A8B40]/30 shadow-md">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-[#4A8B40]" />
            Per-Page HTR Status
          </h3>
          <div className="space-y-2">
            {data.pages.map((p) => (
              <div
                key={p.page_number}
                className="p-3 rounded-xl bg-black/20 border border-[#4A8B40]/20 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2.5">
                  <span className="w-6 h-6 rounded-lg bg-[#4A8B40]/20 text-emerald-300 font-semibold flex items-center justify-center font-mono">
                    {p.page_number}
                  </span>
                  <span className="font-mono text-emerald-100/70">
                    sha256: {p.page_sha256?.slice(0, 12)}...
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded-md font-semibold font-mono text-[11px] ${
                      p.status === "CACHED"
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : p.status === "TRANSCRIBED"
                        ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                        : p.status === "FAILED"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                        : "bg-gray-500/20 text-gray-300"
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
        <div className="p-5 rounded-2xl bg-[#183B25]/40 border border-[#4A8B40]/30 shadow-md">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#4A8B40]" />
            Question Evaluation & Human Reviews
          </h3>
          <div className="max-h-[260px] overflow-y-auto pr-1 space-y-2">
            {data.questions.map((q) => (
              <div
                key={q.question_number}
                className="p-2.5 rounded-xl bg-black/20 border border-[#4A8B40]/20 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white font-mono w-9">
                    Q{q.question_number}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                      q.status === "SCORED"
                        ? "bg-emerald-500/20 text-emerald-300"
                        : q.status === "ROUTED"
                        ? "bg-amber-500/20 text-amber-300"
                        : q.status === "NO_SCHEME"
                        ? "bg-gray-500/20 text-gray-300"
                        : "bg-rose-500/20 text-rose-300"
                    }`}
                  >
                    {q.status}
                  </span>
                  {q.human_reviewed && (
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px] border border-indigo-500/30">
                      <UserCheck className="w-3 h-3 text-indigo-400" />
                      {q.reason_code || "REVIEWED"}
                    </span>
                  )}
                </div>

                <div className="font-mono text-emerald-200 font-bold">
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
      <div className="rounded-2xl bg-[#183B25]/40 border border-[#4A8B40]/30 shadow-md overflow-hidden">
        <button
          onClick={() => setShowEvents(!showEvents)}
          className="w-full p-4 bg-black/20 flex items-center justify-between text-xs font-semibold text-emerald-200 hover:bg-black/30 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#4A8B40]" />
            Chronological Job History ({data.events.length} events logged)
          </div>
          {showEvents ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showEvents && (
          <div className="p-4 max-h-[300px] overflow-y-auto space-y-2 font-mono text-[11px]">
            {data.events.map((evt, idx) => (
              <div
                key={idx}
                className="p-2 rounded-lg bg-black/30 border border-[#4A8B40]/10 flex items-start gap-3"
              >
                <span className="text-emerald-400/60 whitespace-nowrap">
                  {new Date(evt.timestamp).toLocaleTimeString()}
                </span>
                <span className="font-bold text-emerald-300 uppercase min-w-[130px]">
                  {evt.event}
                </span>
                <span className="text-emerald-100/90">{evt.detail}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
