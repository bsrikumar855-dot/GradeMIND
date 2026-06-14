'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { CheckCircle2, ChevronRight, Sparkles, Activity } from 'lucide-react';

const agents = [
  { id: 1, name: 'OCR Agent', desc: 'Extracting text and handwriting from student sheets...' },
  { id: 2, name: 'Understanding Agent', desc: 'Mapping answers to curriculum standards...' },
  { id: 3, name: 'Evaluation Agent', desc: 'Scoring responses based on dynamic rubric...' },
  { id: 4, name: 'Fairness Agent', desc: 'Cross-validating scores to eliminate bias...' },
  { id: 5, name: 'Feedback Agent', desc: 'Generating personalized constructive feedback...' },
  { id: 6, name: 'Report Agent', desc: 'Compiling final analytics and PDF documents...' },
];

export default function EvaluationScreen() {
  const router = useRouter();
  const [currentAgentIndex, setCurrentAgentIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (isComplete) return;

    const totalDuration = 12000; // 12 seconds for the simulation
    const intervalTime = 50;
    const progressIncrement = 100 / (totalDuration / intervalTime);

    const timer = setInterval(() => {
      setProgress((prev) => {
        const next = prev + progressIncrement;
        
        const expectedIndex = Math.floor((next / 100) * agents.length);
        if (expectedIndex !== currentAgentIndex && expectedIndex < agents.length) {
          setCurrentAgentIndex(expectedIndex);
        }

        if (next >= 100) {
          clearInterval(timer);
          setIsComplete(true);
          return 100;
        }
        return next;
      });
    }, intervalTime);

    return () => clearInterval(timer);
  }, [currentAgentIndex, isComplete]);

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
        <AnimatePresence mode="wait">
          {!isComplete ? (
            <motion.div 
              key="processing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -50, filter: 'blur(10px)' }}
              transition={{ duration: 0.5 }}
              className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center"
            >
              {/* Left Side: Circular Progress */}
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

                <div className="text-center max-w-sm">
                  <h2 className="text-2xl font-bold text-brand-dark mb-2">Analyzing Submissions</h2>
                  <p className="text-gray-500">Our agents are currently evaluating the uploaded documents. Please do not close this window.</p>
                </div>
              </div>

              {/* Right Side: Agent Pipeline */}
              <div className="relative">
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
              className="flex flex-col items-center justify-center text-center max-w-2xl mx-auto bg-white p-16 rounded-[2rem] shadow-[0_20px_60px_rgba(47,90,58,0.08)] border border-gray-50"
            >
              <motion.div 
                initial={{ scale: 0 }}
                animate={{ scale: 1, rotate: [0, 10, 0] }}
                transition={{ type: 'spring', damping: 10, delay: 0.2 }}
                className="w-24 h-24 bg-brand-secondary rounded-full flex items-center justify-center mb-8"
              >
                <CheckCircle2 className="w-12 h-12 text-brand-primary" />
              </motion.div>
              
              <h1 className="text-5xl font-extrabold text-brand-dark mb-4 tracking-tight">Evaluation Complete</h1>
              <p className="text-xl text-gray-500 mb-10">
                The AI pipeline has successfully processed all documents. 142 student sheets have been scored and reports are ready.
              </p>
              
              <div className="flex gap-4 w-full">
                <button 
                  onClick={() => router.push('/dashboard')}
                  className="flex-1 px-8 py-4 rounded-xl font-bold text-brand-dark bg-brand-background hover:bg-gray-100 transition-colors border border-gray-200"
                >
                  Return to Dashboard
                </button>
                <button 
                  onClick={() => router.push('/results')}
                  className="flex-1 px-8 py-4 rounded-xl font-bold text-white bg-brand-primary hover:bg-opacity-90 active:scale-95 transition-all shadow-[0_10px_30px_rgba(134,183,123,0.3)] flex items-center justify-center gap-2"
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
