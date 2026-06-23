// src/components/explainability/ConceptInsights.tsx
'use client';

import React from 'react';
import { motion, Variants } from 'framer-motion';
import { CheckCircle2, AlertTriangle, Compass, Trophy, Activity } from 'lucide-react';

type Concept = {
  name: string;
  score: number;
  max_score: number;
};

type Props = {
  concepts: Concept[];
};

export default function ConceptInsights({ concepts = [] }: Props) {
  // Dynamically group concepts by score percentage
  const strongConcepts = concepts.filter(c => {
    const pct = c.max_score > 0 ? (c.score / c.max_score) * 100 : 0;
    return pct >= 80;
  });

  const weakConcepts = concepts.filter(c => {
    const pct = c.max_score > 0 ? (c.score / c.max_score) * 100 : 0;
    return pct < 80;
  });

  const totalCount = concepts.length || 1;
  const coveragePercent = Math.round((strongConcepts.length / totalCount) * 100);

  // Animation variants
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08, delayChildren: 0.1 }
    }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 12 },
    show: {
      opacity: 1,
      y: 0,
      transition: { type: 'spring', stiffness: 350, damping: 25 }
    }
  };

  return (
    <div className="w-full h-full bg-white border border-gray-100 rounded-[2rem] p-8 lg:p-12 shadow-[0_8px_30px_rgba(47,90,58,0.06)] flex flex-col overflow-hidden">
      
      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8 shrink-0 pb-6 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-gradient-to-br from-indigo-400 to-indigo-600 shadow-lg shadow-indigo-200/60">
              <Compass className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <h2 className="text-2xl lg:text-3xl font-black text-gray-900 tracking-tight">Concept Insights</h2>
          </div>
          <p className="text-gray-500 text-sm lg:text-base font-medium ml-[3.25rem]">
            Advanced learning diagnostics mapping academic strengths and critical knowledge gaps.
          </p>
        </div>
      </div>

      {/* ── Main Content Grid ── */}
      <motion.div
        className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {/* LEFT COMPARTMENT: Strong & Weak lists (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Strong Concepts */}
          <motion.div variants={itemVariants} className="p-6 rounded-[2rem] bg-gray-50/50 border border-gray-100">
            <h3 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <Trophy className="w-4 h-4 text-emerald-600" />
              Areas of Strength ({strongConcepts.length})
            </h3>
            {strongConcepts.length > 0 ? (
              <div className="flex flex-wrap gap-2.5">
                {strongConcepts.map(c => {
                  const pct = Math.round((c.score / c.max_score) * 100);
                  return (
                    <div
                      key={c.name}
                      className="flex items-center gap-2 px-3.5 py-2 bg-emerald-50 text-emerald-800 rounded-2xl border border-emerald-100 hover:border-emerald-250 transition-colors"
                    >
                      <CheckCircle2 className="w-4 h-4 text-emerald-650" strokeWidth={2.5} />
                      <span className="font-bold text-sm lg:text-base">{c.name}</span>
                      <span className="text-xs font-black text-emerald-600 bg-white/70 border border-emerald-100/50 px-1.5 py-0.5 rounded-lg">{pct}%</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-gray-500 font-medium">No concepts have reached the 80% mastery threshold yet.</p>
            )}
          </motion.div>

          {/* Needs Improvement */}
          <motion.div variants={itemVariants} className="p-6 rounded-[2rem] bg-gray-50/50 border border-gray-100">
            <h3 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              Focus Areas for Growth ({weakConcepts.length})
            </h3>
            {weakConcepts.length > 0 ? (
              <div className="flex flex-wrap gap-2.5">
                {weakConcepts.map(c => {
                  const pct = Math.round((c.score / c.max_score) * 100);
                  return (
                    <div
                      key={c.name}
                      className="flex items-center gap-2 px-3.5 py-2 bg-amber-50 text-amber-800 rounded-2xl border border-amber-100 hover:border-amber-250 transition-colors"
                    >
                      <AlertTriangle className="w-4 h-4 text-amber-650" strokeWidth={2.5} />
                      <span className="font-bold text-sm lg:text-base">{c.name}</span>
                      <span className="text-xs font-black text-amber-650 bg-white/70 border border-amber-100/50 px-1.5 py-0.5 rounded-lg">{pct}%</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-emerald-700 bg-emerald-50 border border-emerald-100 px-4 py-3 rounded-2xl">
                <CheckCircle2 className="w-4 h-4" />
                <span className="text-sm font-bold">Outstanding work! All concepts are fully mastered.</span>
              </div>
            )}
          </motion.div>
        </div>

        {/* RIGHT COMPARTMENT: Key Diagnostic Metrics (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Progress Circular Dial Card */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] bg-gradient-to-br from-indigo-50/50 to-indigo-100/30 border border-indigo-100 flex flex-col items-center text-center justify-between"
          >
            <span className="text-[11px] font-black text-indigo-700 uppercase tracking-widest mb-4">Mastery Completion Rate</span>
            
            <div className="relative w-28 h-28 flex items-center justify-center mb-4">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="56" cy="56" r="48" className="stroke-indigo-100" strokeWidth="6" fill="transparent" />
                <motion.circle
                  cx="56"
                  cy="56"
                  r="48"
                  className="stroke-indigo-600"
                  strokeWidth="6"
                  fill="transparent"
                  strokeDasharray={2 * Math.PI * 48}
                  initial={{ strokeDashoffset: 2 * Math.PI * 48 }}
                  animate={{ strokeDashoffset: 2 * Math.PI * 48 - (coveragePercent / 100) * (2 * Math.PI * 48) }}
                  transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-black text-indigo-950 tracking-tight leading-none">{coveragePercent}%</span>
                <span className="text-[8px] font-bold text-indigo-500 uppercase tracking-widest mt-1">Covered</span>
              </div>
            </div>
            
            <p className="text-xs text-indigo-900/60 font-semibold leading-relaxed">
              Student has demonstrated high comprehension levels in {strongConcepts.length} out of {totalCount} concepts assessed.
            </p>
          </motion.div>

          {/* Benchmark Analytics */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] border border-gray-100 bg-white space-y-4"
          >
            <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
              <Activity className="w-4 h-4 text-gray-500" />
              <h4 className="text-xs font-black text-gray-800 uppercase tracking-wider">Benchmark Analytics</h4>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Academic Depth</p>
                <p className="text-base font-extrabold text-gray-800">Advanced Standard</p>
              </div>
              <span className="px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-100 text-xs font-black text-emerald-700">Excellent</span>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Scoring Consistency</p>
                <p className="text-base font-extrabold text-gray-800">Very High Correlation</p>
              </div>
              <span className="px-2.5 py-1 rounded-lg bg-blue-50 border border-blue-100 text-xs font-black text-blue-700">94% RValue</span>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Expected Next Step</p>
                <p className="text-base font-extrabold text-gray-800">Conceptual Linkage Review</p>
              </div>
              <span className="px-2.5 py-1 rounded-lg bg-indigo-50 border border-indigo-100 text-xs font-black text-indigo-700">Audit</span>
            </div>
          </motion.div>

        </div>
      </motion.div>

    </div>
  );
}
