// src/components/explainability/AIRecommendations.tsx
'use client';

import React from 'react';
import { motion, Variants } from 'framer-motion';
import { Sparkles, Clock, Target, ArrowUpRight, Zap } from 'lucide-react';

type Props = {
  missingConcepts?: string[];
  score: number;
  max_score: number;
};

export default function AIRecommendations({ missingConcepts = [], score, max_score }: Props) {
  const currentPct = max_score > 0 ? Math.round((score / max_score) * 100) : 0;
  
  // Dynamically calculate estimated improvement based on missing concepts count
  const gapCount = missingConcepts.length;
  const scoreBoost = gapCount > 0 ? Math.min(95 - currentPct, gapCount * 6 + 4) : 8;
  const predictedNextScore = Math.min(100, currentPct + scoreBoost);

  // Generate dynamic recommendations based on missing concepts
  const getActionRoadmap = () => {
    if (gapCount > 0) {
      return [
        {
          phase: 'Phase 1: Conceptual Revision',
          title: `Study missing foundations: ${missingConcepts.slice(0, 2).join(', ')}`,
          detail: 'Re-read textbook sections and watch curated lectures on these exact topics to fill knowledge gaps.',
          time: '3-4 Hours',
          color: 'border-rose-100 bg-rose-50/20 text-rose-700'
        },
        {
          phase: 'Phase 2: Targeted Practice',
          title: 'Solve practice questions on rubric points',
          detail: 'Write active recall summaries of the missing concepts and check them against model answers.',
          time: '2-3 Hours',
          color: 'border-amber-100 bg-amber-50/20 text-amber-700'
        },
        {
          phase: 'Phase 3: AI-Simulated Exam',
          title: 'Take custom adaptive quiz on GradeMIND',
          detail: 'Complete a timed mock quiz focusing exclusively on application problems to ensure long-term retention.',
          time: '1.5 Hours',
          color: 'border-emerald-100 bg-emerald-50/20 text-emerald-700'
        }
      ];
    }

    // Default when student did really well
    return [
      {
        phase: 'Phase 1: Core Concept Linking',
        title: 'Deepen relationships between topics',
        detail: 'Practice writing long answers that synthesize multiple concepts together in a unified argument.',
        time: '2 Hours',
        color: 'border-blue-100 bg-blue-50/20 text-blue-700'
      },
      {
        phase: 'Phase 2: Complex Application',
        title: 'Work on advanced diagnostic problems',
        detail: 'Solve extension and challenge problems from previous olympiads or high-level assessments.',
        time: '3 Hours',
        color: 'border-indigo-100 bg-indigo-50/20 text-indigo-700'
      },
      {
        phase: 'Phase 3: Peer Tutoring',
        title: 'Explain concepts to others',
        detail: 'Teach these topics to peer students or construct sample rubrics to strengthen metacognitive mastery.',
        time: '2 Hours',
        color: 'border-emerald-100 bg-emerald-50/20 text-emerald-700'
      }
    ];
  };

  const steps = getActionRoadmap();

  // Animation variants
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.15 }
    }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, x: -15 },
    show: {
      opacity: 1,
      x: 0,
      transition: { type: 'spring', stiffness: 350, damping: 25 }
    }
  };

  return (
    <div className="w-full h-full bg-white border border-gray-100 rounded-[2rem] p-8 lg:p-12 shadow-[0_8px_30px_rgba(47,90,58,0.06)] flex flex-col overflow-hidden">
      
      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8 shrink-0 pb-6 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-gradient-to-br from-brand-primary to-brand-dark shadow-lg shadow-brand-primary/20">
              <Sparkles className="w-5 h-5 text-white animate-pulse" strokeWidth={2.5} />
            </div>
            <h2 className="text-2xl lg:text-3xl font-black text-gray-900 tracking-tight">AI Recommendations</h2>
          </div>
          <p className="text-gray-500 text-sm lg:text-base font-medium ml-[3.25rem]">
            Personalized, dynamic roadmap engineered to maximize student retention and course grade.
          </p>
        </div>
      </div>

      {/* ── Content Grid ── */}
      <motion.div
        className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {/* LEFT COLUMN: Roadmap Steps Timeline (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <div className="relative pl-6 border-l border-gray-150 space-y-8 py-2 ml-3">
            {steps.map((step, idx) => (
              <motion.div
                key={idx}
                variants={itemVariants}
                className="relative"
              >
                {/* Connector Dot */}
                <div className="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-white border-2 border-brand-primary flex items-center justify-center shadow-sm">
                  <div className="w-1.5 h-1.5 rounded-full bg-brand-primary" />
                </div>

                <div className="space-y-1.5">
                  <span className="text-[11px] font-black text-brand-primary uppercase tracking-widest block">
                    {step.phase}
                  </span>
                  <h4 className="text-lg font-black text-gray-800 tracking-tight">
                    {step.title}
                  </h4>
                  <p className="text-sm text-gray-500 font-medium leading-relaxed max-w-xl">
                    {step.detail}
                  </p>
                  
                  {/* Metadata Tag */}
                  <div className="flex items-center gap-4 pt-1">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-gray-400">
                      <Clock className="w-3.5 h-3.5 text-gray-400" />
                      <span>{step.time}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs font-bold text-gray-400">
                      <Target className="w-3.5 h-3.5 text-gray-400" />
                      <span>Conceptual Alignment</span>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* RIGHT COLUMN: Predicted Grade & Diagnostics (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Estimated Improvement Ring Card */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] bg-gradient-to-br from-brand-secondary/40 to-brand-primary/5 border border-brand-primary/10 flex flex-col items-center text-center relative overflow-hidden"
          >
            {/* Background sparkle decoration */}
            <div className="absolute top-2 right-2 opacity-10">
              <Zap className="w-24 h-24 text-brand-primary" />
            </div>

            <span className="text-[11px] font-black text-brand-primary uppercase tracking-widest mb-4">Target Outcome Analysis</span>
            
            {/* Dial representation */}
            <div className="relative w-36 h-36 flex items-center justify-center mb-4">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="72" cy="72" r="60" className="stroke-gray-200/50" strokeWidth="8" fill="transparent" />
                <motion.circle
                  cx="72"
                  cy="72"
                  r="60"
                  className="stroke-brand-primary"
                  strokeWidth="8"
                  fill="transparent"
                  strokeDasharray={2 * Math.PI * 60}
                  initial={{ strokeDashoffset: 2 * Math.PI * 60 }}
                  animate={{ strokeDashoffset: 2 * Math.PI * 60 - (predictedNextScore / 100) * (2 * Math.PI * 60) }}
                  transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-black text-gray-850 tracking-tight leading-none">
                  {predictedNextScore}%
                </span>
                <span className="text-[8px] font-bold text-gray-450 uppercase tracking-widest mt-1.5">
                  Target Score
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1.5 px-3 py-1 bg-white border border-brand-primary/15 rounded-full text-xs font-black text-brand-primary uppercase tracking-wider mb-2.5">
              <ArrowUpRight className="w-3.5 h-3.5" />
              Est. Boost +{scoreBoost}%
            </div>

            <p className="text-xs text-gray-500 font-medium px-4 leading-relaxed">
              Completing this study path is predicted to elevate the next score to {predictedNextScore}%.
            </p>
          </motion.div>

          {/* Diagnostic tags */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] border border-gray-100 bg-white space-y-4"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Priority Level</p>
                <p className="text-base font-extrabold text-gray-800">
                  {gapCount > 1 ? 'High Priority' : 'Medium Priority'}
                </p>
              </div>
              <span className={`px-2.5 py-1 rounded-lg text-xs font-black uppercase tracking-wider border ${gapCount > 1 ? 'bg-rose-50 border-rose-100 text-rose-700' : 'bg-blue-50 border-blue-100 text-blue-700'}`}>
                {gapCount > 1 ? 'Urgent' : 'Routine'}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Estimated Practice</p>
                <p className="text-base font-extrabold text-gray-800">
                  {gapCount > 0 ? `${gapCount * 2} Units` : '4 Practice Sets'}
                </p>
              </div>
              <span className="px-2.5 py-1 rounded-lg bg-gray-50 border border-gray-100 text-xs font-black text-gray-700">Self-paced</span>
            </div>
          </motion.div>

        </div>
      </motion.div>

    </div>
  );
}
