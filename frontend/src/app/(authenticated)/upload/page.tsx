'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  UploadCloud, 
  FileText, 
  Trash2, 
  Sparkles, 
  AlertCircle,
  CheckCircle2,
  FileCheck,
  Zap,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';
import { SpotlightCard, ShimmerBadge, BorderBeam, MagicBentoCard, PageHeroBanner } from '@/components/ui';
import { JobProgressState } from '@/components/ui/job-progress-state';

export default function UploadCenter() {
  const router = useRouter();

  const [paper, setPaper] = useState<File | null>(null);
  const [answers, setAnswers] = useState<File | null>(null);
  const [scheme, setScheme] = useState<File | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [isOffline, setIsOffline] = useState(false);

  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const progressRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (activeJobId && progressRef.current) {
      progressRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [activeJobId]);

  const handleStartEvaluation = async () => {
    setSubmitError('');
    if (!paper || !answers || !scheme) {
      setSubmitError('Please upload all three required files: Question Paper, Answer Sheet, and Marking Scheme.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await SubmissionService.gradeV2(paper, answers, scheme, undefined, undefined, isOffline);
      if (res.job_id) {
        setActiveJobId(res.job_id);
        setIsSubmitting(false);
      } else {
        throw new Error('Failed to start grading job: No job_id returned.');
      }
    } catch (err: any) {
      console.error('Submission failed:', err);
      setSubmitError(err.message || 'An error occurred during evaluation setup.');
      setIsSubmitting(false);
    }
  };

  const FileDropzone = ({ 
    label, 
    subtitle,
    file, 
    setFile, 
    accept 
  }: { 
    label: string, 
    subtitle: string,
    file: File | null, 
    setFile: (f: File | null) => void,
    accept: string
  }) => (
    <MagicBentoCard showBeam={!!file} className="p-5 flex-1 flex flex-col justify-between min-h-[300px] text-left border-2 border-emerald-800/30">
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-xs font-black text-black uppercase tracking-wider">{label} *</label>
          {file && (
            <ShimmerBadge variant="emerald">
              <CheckCircle2 className="w-3.5 h-3.5 text-[#183B25]" /> Attached
            </ShimmerBadge>
          )}
        </div>
        <p className="text-xs text-black font-bold">{subtitle}</p>
      </div>

      {!file ? (
        <div className="flex-1 border-2 border-dashed border-emerald-400 hover:border-[#183B25] bg-emerald-50/60 hover:bg-emerald-100/60 rounded-xl p-6 text-center transition-all flex flex-col items-center justify-center my-3 group">
          <div className="p-3 rounded-full bg-white border-2 border-emerald-500 shadow-xs mb-3 group-hover:scale-105 transition-transform">
            <UploadCloud className="w-8 h-8 text-[#183B25]" />
          </div>
          <p className="text-xs font-black text-black mb-1">Drag & drop {label}</p>
          <p className="text-[11px] text-black font-bold mb-4">Supports PDF or Image files up to 25MB</p>
          
          <label className="inline-block px-4 py-2 bg-[#183B25] hover:bg-[#112B1B] text-white font-black text-xs rounded-xl cursor-pointer transition-colors shadow-xs">
            Browse File
            <input 
              type="file" 
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setFile(e.target.files[0]);
                }
              }} 
              accept={accept} 
              className="hidden" 
            />
          </label>
        </div>
      ) : (
        <div className="flex-1 p-5 rounded-xl bg-emerald-100/80 border-2 border-emerald-400 flex flex-col justify-between my-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-lg bg-[#183B25] text-white shrink-0 shadow-xs">
                <FileText className="w-5 h-5" />
              </div>
              <div className="truncate">
                <span className="font-black text-black text-xs block truncate">{file.name}</span>
                <span className="text-[11px] text-black font-extrabold block mt-0.5">{(file.size / 1024).toFixed(1)} KB</span>
              </div>
            </div>
            <button 
              onClick={() => setFile(null)} 
              className="text-black hover:text-rose-700 p-1.5 rounded-lg hover:bg-white transition-colors shrink-0"
              title="Remove file"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>

          <div className="pt-3 border-t-2 border-emerald-300 flex items-center justify-between text-[11px]">
            <span className="text-black font-black flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4 text-[#183B25]" /> Validated format
            </span>
            <span className="text-black font-black uppercase">{file.name.split('.').pop()}</span>
          </div>
        </div>
      )}

      <div className="text-[11px] text-black font-bold pt-1">
        Required for value-point match evaluation
      </div>
    </MagicBentoCard>
  );

  return (
    <div className="flex-1 flex flex-col justify-between space-y-5 text-left w-full text-black">
      
      {/* 1. Elevated Reference Picture Hero Banner */}
      <PageHeroBanner
        badgeLabel="ASSESSMENT MANAGEMENT REPOSITORY"
        badgeIcon={<UploadCloud className="w-3.5 h-3.5 text-emerald-400" />}
        title="Upload Answer Script"
        subtitle="Submit a Question Paper, Answer Sheet, and Marking Scheme JSON for deterministic evaluation."
        statLabel="ENGINE VERSION"
        statValue="v2 Autonomous"
      />

      {/* Error Notice */}
      {submitError && (
        <div className="p-3.5 rounded-xl bg-rose-50 border-2 border-rose-300 text-rose-800 text-xs font-black flex items-center gap-2.5 shrink-0">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{submitError}</span>
        </div>
      )}

      {/* 2. 3-Column Dropzone Grid */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-5 items-stretch min-h-[320px]">
        <FileDropzone 
          label="Question Paper" 
          subtitle="Master examination question paper document"
          file={paper} 
          setFile={setPaper} 
          accept="image/*,.pdf" 
        />

        <FileDropzone 
          label="Marking Scheme" 
          subtitle="JSON structured value-point criteria & rules"
          file={scheme} 
          setFile={setScheme} 
          accept=".json" 
        />

        <FileDropzone 
          label="Student Answer Sheet" 
          subtitle="Handwritten or typed student answer script"
          file={answers} 
          setFile={setAnswers} 
          accept="image/*,.pdf" 
        />
      </div>

      {/* 3. Execution Control Bar */}
      <MagicBentoCard className="p-4 md:p-5 w-full flex flex-row items-center justify-between gap-4 shrink-0 border-2 border-emerald-800/30 bg-white">
        <div className="flex items-center gap-3">
          <input 
            type="checkbox" 
            id="offline-mode" 
            checked={isOffline} 
            onChange={(e) => setIsOffline(e.target.checked)}
            className="w-4 h-4 text-[#183B25] bg-emerald-50 border-emerald-400 rounded focus:ring-[#4A8B40] cursor-pointer"
          />
          <label htmlFor="offline-mode" className="text-xs font-black text-black cursor-pointer">
            Run in Offline Mode <span className="text-black font-bold">(uses cached model responses, no live network calls)</span>
          </label>
        </div>

        <div className="flex items-center gap-3 ml-auto shrink-0">
          {activeJobId && (
            <button
              onClick={() => router.push(`/results?job_id=${activeJobId}`)}
              className="px-5 py-3 bg-[#183B25] hover:bg-[#112a1a] text-white font-black text-xs md:text-sm rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-md border-2 border-emerald-400 cursor-pointer animate-pulse"
            >
              <Zap className="w-4 h-4 text-emerald-400" />
              <span>View Results</span>
              <ArrowRight className="w-4 h-4 text-emerald-400" />
            </button>
          )}

          <button
            onClick={handleStartEvaluation}
            disabled={isSubmitting}
            className="px-6 py-3 bg-[#4A8B40] hover:bg-[#3B7233] text-white font-black text-xs md:text-sm rounded-xl transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.99] flex items-center justify-center gap-2.5 shadow-md border-2 border-emerald-500 shrink-0 group cursor-pointer opacity-100"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Processing Evaluation Job...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-emerald-200 group-hover:rotate-12 transition-transform duration-300" />
                <span>Start Autonomous Evaluation</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" />
              </>
            )}
          </button>
        </div>
      </MagicBentoCard>

      {/* 4. Active Job Progress & Preservation State */}
      {activeJobId && (
        <div ref={progressRef} id="job-progress-container" className="w-full mt-6 scroll-mt-6">
          <JobProgressState jobId={activeJobId} />
        </div>
      )}

    </div>
  );
}
