// src/components/explainability/MissingConceptsCard.tsx
'use client';

import React from 'react';
import { motion, Variants } from 'framer-motion';
import { XCircle, AlertTriangle, BookOpen, ShieldAlert, Activity } from 'lucide-react';

type Props = {
  missing: string[];
};

export default function MissingConceptsCard({ missing }: Props) {
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.12, delayChildren: 0.15 } }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, x: -12 },
    show: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 400, damping: 30 } }
  };

  const gapCount = missing?.length || 0;
  
  // Calculate dynamic grade impact and coverage
  const impactScoreLoss = gapCount * 6;
  const rubricCoverage = Math.max(40, 100 - gapCount * 12);

  // SVG Radial Dial dimensions
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (rubricCoverage / 100) * circumference;

  return (
    <div className="w-full h-full bg-white rounded-[2rem] p-8 md:p-12 lg:p-14 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 flex flex-col overflow-hidden">
      
      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8 shrink-0 pb-6 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-gradient-to-br from-rose-400 to-rose-600 shadow-lg shadow-rose-200/60">
              <AlertTriangle className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <h3 className="text-2xl lg:text-3xl font-black text-gray-900 tracking-tight">Missing Concepts</h3>
          </div>
          <p className="text-gray-500 text-sm lg:text-base font-medium ml-[3.25rem]">
            Critical topics expected by the rubric but not addressed in the student&apos;s response.
          </p>
        </div>

        {/* Global audit status badge */}
        {gapCount > 0 && (
          <div className="flex items-center gap-2 bg-rose-50 border border-rose-100 rounded-2xl px-4 py-2 ml-[3.25rem] md:ml-0 self-start md:self-center shrink-0 animate-pulse">
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <span className="text-xs font-black text-rose-700 uppercase tracking-widest">Gaps Detected</span>
          </div>
        )}
      </div>

      {/* ── Grid Container ── */}
      <motion.div
        className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {/* LEFT COLUMN: Missing Concepts List (7 cols) */}
        <div className="lg:col-span-7 flex flex-col justify-start">
          {missing && missing.length > 0 ? (
            <div className="space-y-3.5">
              {missing.map((c, i) => (
                <motion.div
                  key={i}
                  variants={itemVariants}
                  className="flex items-start gap-4 p-4 rounded-2xl bg-gray-50/50 border border-gray-100 hover:bg-rose-50/20 hover:border-rose-200/50 transition-colors duration-300 group"
                >
                  <div className="p-2 rounded-xl bg-white shadow-sm border border-gray-100 text-rose-500 shrink-0 mt-0.5 group-hover:scale-105 transition-transform duration-300">
                    <XCircle className="w-5 h-5" strokeWidth={2.5} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-lg md:text-xl lg:text-2xl font-extrabold text-gray-800 tracking-tight leading-snug block">{c}</span>
                    <p className="text-sm lg:text-base text-gray-500 mt-1 font-medium leading-relaxed">
                      Expected topic was omitted from the answer structure.
                    </p>
                  </div>
                  <div className="shrink-0 px-2.5 py-0.5 rounded-lg bg-rose-150 text-[11px] lg:text-xs font-black text-rose-700 uppercase tracking-widest self-center">
                    Not Found
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 py-12">
              <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-100">
                <BookOpen className="w-8 h-8 text-emerald-500" />
              </div>
              <p className="text-xl text-gray-600 font-bold">All concepts covered</p>
              <p className="text-sm text-gray-400 font-medium">The student addressed every required topic successfully.</p>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Diagnostic Scores & Bullet Insights (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Circular Rubric Coverage Card */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] bg-gradient-to-br from-rose-50/50 to-rose-100/30 border border-rose-105 flex flex-col items-center text-center justify-between"
          >
            <span className="text-xs lg:text-sm font-black text-rose-700 uppercase tracking-widest mb-4">Rubric Coverage Index</span>
            
            <div className="relative w-28 h-28 flex items-center justify-center mb-4">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="56" cy="56" r="48" className="stroke-rose-100" strokeWidth="6" fill="transparent" />
                <motion.circle
                  cx="56"
                  cy="56"
                  r="48"
                  className="stroke-rose-500"
                  strokeWidth="6"
                  fill="transparent"
                  strokeDasharray={circumference}
                  initial={{ strokeDashoffset: circumference }}
                  animate={{ strokeDashoffset }}
                  transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-black text-rose-950 tracking-tight leading-none">{rubricCoverage}%</span>
                <span className="text-[9px] lg:text-xs font-bold text-rose-500 uppercase tracking-widest mt-1">Coverage</span>
              </div>
            </div>
            
            <p className="text-sm lg:text-base text-rose-900/70 font-semibold leading-relaxed">
              Answer covers {rubricCoverage}% of required concept clusters.
            </p>
          </motion.div>

          {/* Diagnostic indicators */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] border border-gray-100 bg-white space-y-4"
          >
            <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
              <Activity className="w-4 h-4 text-gray-500" />
              <h4 className="text-sm lg:text-base font-black text-gray-800 uppercase tracking-wider">Estimated Score Impact</h4>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Estimated Points Loss</p>
                <p className="text-base font-extrabold text-gray-800">-{impactScoreLoss}% potential penalty</p>
              </div>
              <span className="px-2 py-0.5 rounded-lg bg-rose-50 border border-rose-100 text-xs font-black text-rose-700">Negative</span>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Severity Status</p>
                <p className="text-base font-extrabold text-gray-800">
                  {gapCount > 2 ? 'Significant Deficiency' : 'Moderate Deficiency'}
                </p>
              </div>
              <span className={`px-2 py-0.5 rounded-lg text-xs font-black uppercase tracking-widest border ${gapCount > 2 ? 'bg-red-50 border-red-100 text-red-700' : 'bg-amber-50 border-amber-100 text-amber-700'}`}>
                {gapCount > 2 ? 'Critical' : 'Warning'}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Target Recommendation</p>
                <p className="text-base font-extrabold text-gray-800">Adaptive Remediation Quiz</p>
              </div>
              <span className="px-2 py-0.5 rounded-lg bg-indigo-50 border border-indigo-100 text-xs font-black text-indigo-700">Assigned</span>
            </div>
          </motion.div>

        </div>
      </motion.div>

    </div>
  );
}
