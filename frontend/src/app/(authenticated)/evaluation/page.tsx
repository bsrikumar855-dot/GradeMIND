'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter, useSearchParams } from 'next/navigation';
import { CheckCircle2, XCircle, ChevronRight, Sparkles, Activity } from 'lucide-react';
import { SubmissionService } from '@/services/submission.service';

const agents = [
  { id: 1, name: 'OCR Agent', desc: 'Extracting text and handwriting from student sheets...' },
  { id: 2, name: 'Understanding Agent', desc: 'Mapping answers to curriculum standards...' },
  { id: 3, name: 'Evaluation Agent', desc: 'Scoring responses based on dynamic rubric...' },
  { id: 4, name: 'Fairness Agent', desc: 'Cross-validating scores to eliminate bias...' },
  { id: 5, name: 'Feedback Agent', desc: 'Generating personalized constructive feedback...' },
  { id: 6, name: 'Report Agent', desc: 'Compiling final analytics and PDF documents...' },
];

function EvaluationContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const idsStr = searchParams.get('ids');
  
  const [submissionIds, setSubmissionIds] = useState<string[]>([]);
  const [submissions, setSubmissions] = useState<Record<string, any>>({});
  const [progress, setProgress] = useState(0);
  const [currentAgentIndex, setCurrentAgentIndex] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [loadError, setLoadError] = useState('');

  // Latest submissions, readable from the poller below without making
  // `submissions` a dependency of that effect (see comment there).
  const submissionsRef = React.useRef(submissions);
  useEffect(() => {
    submissionsRef.current = submissions;
  }, [submissions]);

  // Parse submission IDs from query
  useEffect(() => {
    if (idsStr) {
      setSubmissionIds(idsStr.split(',').filter(Boolean));
    }
  }, [idsStr]);

  // Status Poller
  useEffect(() => {
    if (submissionIds.length === 0) return;

    let active = true;

    const fetchStatuses = async () => {
      try {
        const nextSubmissions: Record<string, any> = { ...submissionsRef.current };
        let updatedAny = false;

        await Promise.all(
          submissionIds.map(async (id) => {
            // Only poll if not already finalized
            const current = submissionsRef.current[id];
            if (current && (current.status === 'COMPLETED' || current.status === 'FAILED')) {
              return;
            }

            try {
              const res = await SubmissionService.getStatus(id);
              if (res.success && res.data) {
                // If it's first load, get full details to have student name
                if (!current || !current.student_name) {
                  const detailsRes = await SubmissionService.getSubmissionById(id);
                  nextSubmissions[id] = {
                    ...res.data,
                    student_name: detailsRes.success ? detailsRes.data.student_name : `Student (${id.substring(0, 4)})`,
                    student_roll_number: detailsRes.success ? detailsRes.data.student_roll_number : 'N/A'
                  };
                } else {
                  nextSubmissions[id] = {
                    ...current,
                    ...res.data
                  };
                }
                updatedAny = true;
              }
            } catch (err) {
              console.error(`Failed to poll status for ${id}:`, err);
              nextSubmissions[id] = {
                ...(current || { id }),
                status: 'FAILED',
                error_message: 'Evaluation could not be completed. Please retry the submission.'
              };
              updatedAny = true;
            }
          })
        );

        if (!active) return;

        if (updatedAny) {
          setSubmissions(nextSubmissions);

          // Calculate progress & current agent index
          // Status weightings:
          // UPLOADED = 15%
          // PROCESSING = 40% (OCR running)
          // OCR_COMPLETE = 55%
          // EVALUATING = 75% (Rubrics running)
          // COMPLETED = 100%
          // FAILED = 100%
          const items = Object.values(nextSubmissions);
          if (items.length > 0) {
            let totalProgressSum = 0;
            let ocrRunning = false;
            let evalRunning = false;
            let completed = 0;
            let failed = 0;

            items.forEach((sub: any) => {
              if (sub.status === 'COMPLETED') {
                totalProgressSum += 100;
                completed++;
              } else if (sub.status === 'FAILED') {
                totalProgressSum += 100;
                failed++;
              } else if (sub.status === 'EVALUATING') {
                totalProgressSum += 75;
                evalRunning = true;
              } else if (sub.status === 'OCR_COMPLETE') {
                totalProgressSum += 55;
              } else if (sub.status === 'PROCESSING') {
                totalProgressSum += 40;
                ocrRunning = true;
              } else {
                totalProgressSum += 15;
              }
            });

            const avgProgress = totalProgressSum / items.length;
            setProgress(avgProgress);

            // Dynamically assign active agent step
            if (completed + failed === items.length) {
              setCurrentAgentIndex(5);
              setIsComplete(true);
            } else if (evalRunning) {
              // Evaluating stages (Rubrics/Fairness/Feedback)
              if (avgProgress > 80) {
                setCurrentAgentIndex(4); // Feedback Agent
              } else if (avgProgress > 70) {
                setCurrentAgentIndex(3); // Fairness Agent
              } else {
                setCurrentAgentIndex(2); // Evaluation Agent
              }
            } else if (ocrRunning) {
              setCurrentAgentIndex(0); // OCR Agent
            } else {
              // Pre-processing or intermediate
              setCurrentAgentIndex(1); // Understanding Agent
            }
          }
        }
      } catch (err) {
        console.error('Poller error:', err);
        if (active) {
          setLoadError('Evaluation could not be completed. Please retry the submission.');
        }
      }
    };

    // Initial load
    fetchStatuses();

    // Schedule poller
    const interval = setInterval(() => {
      fetchStatuses();
    }, 2000);

    return () => {
      active = false;
      clearInterval(interval);
    };
    // Deliberately NOT depending on `submissions`: this effect calls
    // setSubmissions itself, so including it would tear down and recreate
    // the poller (plus fire an immediate extra fetch) on every single poll
    // response, turning a 2s interval into a request storm. Latest
    // submissions state is read via submissionsRef instead.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submissionIds]);

  const subList = Object.values(submissions);

  return (
    <div className="min-h-screen bg-brand-background flex items-center justify-center p-8 overflow-hidden">
      
      {/* Decorative Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
        <motion.div 
          className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] bg-brand-accent/5 rounded-full blur-[120px]"
          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div 
          className="absolute top-[60%] -right-[10%] w-[40%] h-[60%] bg-brand-primary/5 rounded-full blur-[120px]"
          animate={{ scale: [1, 1.5, 1], opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        />
      </div>

      <div className="max-w-6xl w-full relative z-10">
        {loadError && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 rounded-2xl p-4 font-semibold">
            {loadError}
          </div>
        )}
        <AnimatePresence mode="wait">
          {!isComplete ? (
            <motion.div 
              key="processing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -50, filter: 'blur(10px)' }}
              transition={{ duration: 0.5 }}
              className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-start"
            >
              {/* Left Side: Circular Progress & Student List */}
              <div className="flex flex-col items-center justify-center">
                <div className="relative mb-8">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                    className="absolute inset-0 rounded-full border border-dashed border-gray-200 scale-[1.15]"
                  />
                  <div className="relative w-72 h-72 flex items-center justify-center bg-white rounded-full shadow-[0_0_50px_rgba(91,141,239,0.1)]">
                    <svg className="absolute w-full h-full transform -rotate-90 p-4" viewBox="0 0 100 100">
                      <circle cx="50" cy="50" r="46" fill="none" stroke="#F3F4F6" strokeWidth="4" />
                      <motion.circle 
                        cx="50" cy="50" r="46" fill="none" 
                        stroke="url(#gradient)"
                        strokeWidth="6"
                        strokeLinecap="round"
                        initial={{ pathLength: 0 }}
                        animate={{ pathLength: progress / 100 }}
                        transition={{ duration: 0.1, ease: 'linear' }}
                      />
                      <defs>
                        <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#5B8DEF" />
                          <stop offset="100%" stopColor="#86B77B" />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <motion.div
                        initial={{ scale: 0.8 }}
                        animate={{ scale: 1 }}
                        transition={{ repeat: Infinity, repeatType: "reverse", duration: 1 }}
                      >
                        <Sparkles className="w-8 h-8 text-brand-accent mb-2 opacity-50" />
                      </motion.div>
                      <span className="text-7xl font-extrabold text-brand-dark tracking-tighter">
                        {Math.floor(progress)}<span className="text-4xl text-gray-400">%</span>
                      </span>
                      <span className="text-xs font-bold text-brand-accent uppercase tracking-[0.2em] mt-2">
                        AI Processing
                      </span>
                    </div>
                  </div>
                </div>

                <div className="text-center max-w-sm mb-6">
                  <h2 className="text-2xl font-bold text-brand-dark mb-2">Analyzing Submissions</h2>
                  <p className="text-gray-500 text-sm">Our agents are currently evaluating the uploaded documents. Please do not close this window.</p>
                </div>

                {/* Submissions Batch list */}
                <div className="w-full bg-white p-6 rounded-2xl border border-gray-100 shadow-sm max-h-[200px] overflow-y-auto space-y-2">
                  <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Active Batch Status</div>
                  {subList.map((sub: any) => (
                    <div key={sub.id} className="flex items-center justify-between text-sm py-1.5 border-b border-gray-50 last:border-0">
                      <div className="flex flex-col">
                        <span className="font-bold text-brand-dark">{sub.student_name}</span>
                        <span className="text-xs text-gray-400">Roll: {sub.student_roll_number}</span>
                        {sub.error_message && (
                          <span className="text-xs text-red-500 mt-1">Evaluation could not be completed. Please retry the submission.</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          sub.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                          sub.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                          'bg-blue-100 text-blue-700 animate-pulse'
                        }`}>
                          {sub.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right Side: Agent Pipeline */}
              <div className="relative w-full">
                {/* Connecting background line */}
                <div className="absolute left-[27px] top-6 bottom-6 w-0.5 bg-gray-200/50 rounded-full" />
                
                <div className="space-y-2 relative">
                  {agents.map((agent, idx) => {
                    const isCompleted = currentAgentIndex > idx;
                    const isActive = currentAgentIndex === idx;

                    return (
                      <motion.div 
                        key={agent.id}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className={`relative flex items-center gap-6 p-5 rounded-2xl transition-all duration-500 ${
                          isActive ? 'bg-white shadow-[0_10px_40px_rgba(91,141,239,0.12)] border border-brand-accent/20 scale-[1.02] z-10 translate-x-2' : 
                          'bg-transparent border border-transparent hover:bg-white/40'
                        }`}
                      >
                        {/* Status Icon */}
                        <div className="relative z-10">
                          <motion.div 
                            className={`flex items-center justify-center w-14 h-14 rounded-full border-2 transition-all duration-500 ${
                              isCompleted ? 'bg-brand-primary border-brand-primary text-white shadow-lg shadow-brand-primary/20' : 
                              isActive ? 'bg-white border-brand-accent text-brand-accent' : 
                              'bg-white border-gray-200 text-gray-300'
                            }`}
                            animate={isActive ? { boxShadow: ['0 0 0 0 rgba(91,141,239,0.4)', '0 0 0 15px rgba(91,141,239,0)'] } : {}}
                            transition={isActive ? { duration: 1.5, repeat: Infinity } : {}}
                          >
                            {isCompleted ? <CheckCircle2 className="w-6 h-6" /> : isActive ? <Activity className="w-6 h-6 animate-pulse" /> : <span className="font-bold">{agent.id}</span>}
                          </motion.div>
                          
                          {/* Active Line Fill */}
                          {isActive && idx !== agents.length - 1 && (
                            <motion.div 
                              className="absolute top-14 left-1/2 -translate-x-1/2 w-0.5 bg-gradient-to-b from-brand-accent to-transparent"
                              initial={{ height: 0 }}
                              animate={{ height: 80 }}
                              transition={{ duration: 1.5, repeat: Infinity }}
                            />
                          )}
                          {isCompleted && idx !== agents.length - 1 && (
                            <div className="absolute top-14 left-1/2 -translate-x-1/2 w-0.5 h-full bg-brand-primary" />
                          )}
                        </div>

                        {/* Text */}
                        <div className="flex-1 pt-1">
                          <h3 className={`text-lg font-bold transition-colors duration-300 ${
                            isActive ? 'text-brand-accent' : isCompleted ? 'text-brand-dark' : 'text-gray-400'
                          }`}>
                            {agent.name}
                          </h3>
                          <motion.p 
                            className={`text-sm mt-1 transition-colors duration-300 ${isActive ? 'text-brand-dark/70' : 'text-gray-400'}`}
                            initial={false}
                            animate={isActive ? { opacity: [0.5, 1, 0.5] } : { opacity: 1 }}
                            transition={isActive ? { duration: 2, repeat: Infinity } : {}}
                          >
                            {agent.desc}
                          </motion.p>
                        </div>
                      </motion.div>
                    )
                  })}
                </div>
              </div>
            </motion.div>
          ) : (
            /* Completion Screen */
            <motion.div 
              key="complete"
              initial={{ opacity: 0, scale: 0.9, filter: 'blur(10px)' }}
              animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
              transition={{ duration: 0.7, type: 'spring' }}
              className="flex flex-col items-center justify-center text-center max-w-2xl mx-auto bg-white p-12 rounded-[2rem] shadow-[0_20px_60px_rgba(47,90,58,0.08)] border border-gray-50"
            >
              <motion.div 
                initial={{ scale: 0 }}
                animate={{ scale: 1, rotate: [0, 10, 0] }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
                className="w-20 h-20 bg-brand-secondary rounded-full flex items-center justify-center mb-6"
              >
                <CheckCircle2 className="w-10 h-10 text-brand-primary" />
              </motion.div>
              
              <h1 className="text-4xl font-extrabold text-brand-dark mb-3 tracking-tight">Evaluation Complete</h1>
              <p className="text-base text-gray-500 mb-8">
                The AI pipeline has successfully processed all documents. {subList.length} student sheets have been scored and reports are ready.
              </p>

              {/* Breakdown List */}
              <div className="w-full bg-gray-50 p-6 rounded-2xl mb-8 max-h-48 overflow-y-auto space-y-2 border border-gray-100 text-left">
                <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Grading Breakdown</div>
                {subList.map((sub: any) => (
                  <div key={sub.id} className="flex items-center justify-between text-sm py-1 border-b border-gray-100 last:border-0">
                    <div>
                      <span className="font-bold text-brand-dark">{sub.student_name}</span>
                      <span className="text-xs text-gray-400 ml-2">Roll: {sub.student_roll_number}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {sub.status === 'FAILED' ? (
                        <span className="text-red-500 flex items-center gap-1 text-xs font-bold">
                          <XCircle className="w-4 h-4" /> Failed
                        </span>
                      ) : (
                        <span className="font-extrabold text-brand-primary">
                          {sub.obtained_marks !== null ? `${sub.obtained_marks} / ${sub.total_marks || 100}` : 'Graded'}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="flex gap-4 w-full">
                <button 
                  onClick={() => router.push('/dashboard')}
                  className="flex-1 px-8 py-3.5 rounded-xl font-bold text-brand-dark bg-brand-background hover:bg-gray-100 transition-colors border border-gray-200"
                >
                  Return to Dashboard
                </button>
                <button 
                  onClick={() => router.push(`/results?submissionId=${submissionIds[0]}`)}
                  className="flex-1 px-8 py-3.5 rounded-xl font-bold text-white bg-brand-primary hover:bg-opacity-90 active:scale-95 transition-all shadow-md flex items-center justify-center gap-2"
                >
                  View Full Results
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function EvaluationScreen() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-brand-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-4 border-brand-primary border-t-transparent"></div>
      </div>
    }>
      <EvaluationContent />
    </Suspense>
  );
}

