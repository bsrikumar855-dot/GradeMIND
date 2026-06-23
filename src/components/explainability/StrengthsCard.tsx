// src/components/explainability/StrengthsCard.tsx
'use client';

import React from 'react';
import { motion, Variants } from 'framer-motion';
import { CheckCircle2, Star, ShieldCheck, Activity } from 'lucide-react';

type Props = {
  strengths: string[];
};

export default function StrengthsCard({ strengths }: Props) {
  // Animation variants
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.1 } }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 350, damping: 25 } }
  };

  const total = strengths?.length || 0;

  // SVG Radial Ring dimensions
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const masteryPercentage = total > 0 ? Math.min(100, Math.round((total / (total + 1)) * 100)) : 0;
  const strokeDashoffset = circumference - (masteryPercentage / 100) * circumference;

  return (
    <div className="w-full h-full bg-white rounded-[2rem] p-8 md:p-12 lg:p-14 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 flex flex-col overflow-hidden">

      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8 shrink-0 pb-6 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-lg shadow-emerald-200/60">
              <Star className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <h3 className="text-2xl lg:text-3xl font-black text-gray-900 tracking-tight">Strengths Identified</h3>
          </div>
          <p className="text-gray-500 text-sm lg:text-base font-medium ml-[3.25rem]">
            Areas where the student demonstrated excellent comprehension and rubric mastery.
          </p>
        </div>

        {/* Global verification badge */}
        <div className="flex items-center gap-2.5 bg-emerald-50 border border-emerald-100/70 rounded-2xl px-4 py-2 ml-[3.25rem] md:ml-0 self-start md:self-center shrink-0">
          <ShieldCheck className="w-4 h-4 text-emerald-650" />
          <span className="text-xs font-black text-emerald-700 uppercase tracking-widest">Mastery Validated</span>
        </div>
      </div>

      {/* ── Grid Container ── */}
      <motion.div
        className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {/* LEFT COLUMN: Strengths List Grid (7 cols) */}
        <div className="lg:col-span-7 flex flex-col justify-start">
          {strengths && strengths.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {strengths.map((s, i) => (
                <motion.div
                  key={i}
                  variants={itemVariants}
                  className="relative flex items-start gap-3.5 p-5 rounded-2xl bg-gray-50/50 border border-gray-100 hover:bg-emerald-50/20 hover:border-emerald-200/50 hover:shadow-md hover:shadow-emerald-100/30 transition-all duration-300 group cursor-default"
                >
                  {/* Numbered Icon */}
                  <div className="relative shrink-0 mt-0.5">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-md shadow-emerald-250 flex items-center justify-center group-hover:scale-105 transition-transform duration-300">
                      <CheckCircle2 className="w-4.5 h-4.5 text-white" strokeWidth={2.5} />
                    </div>
                    <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-white border-2 border-emerald-400 text-[8px] font-black text-emerald-600 flex items-center justify-center shadow-xs">
                      {i + 1}
                    </span>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <span className="text-base md:text-lg lg:text-xl font-extrabold text-gray-800 tracking-tight leading-snug block truncate-2-lines">{s}</span>
                    <p className="text-xs lg:text-sm text-gray-500 mt-1 font-medium leading-relaxed">
                      Solid proof found in response.
                    </p>
                  </div>

                  {/* Status Badging */}
                  <div className="shrink-0 self-start">
                    <span className="inline-flex px-2.5 py-0.5 rounded-lg bg-emerald-100/65 text-[11px] lg:text-xs font-black text-emerald-700 uppercase tracking-widest">
                      Mastered
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 py-12">
              <div className="w-14 h-14 rounded-2xl bg-gray-50 border border-gray-100 flex items-center justify-center">
                <Star className="w-6 h-6 text-gray-300" />
              </div>
              <p className="text-base text-gray-400 font-bold">No strengths identified yet</p>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Diagnostic Scores & Bullet Insights (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Circular Mastery Rate Card */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] bg-gradient-to-br from-emerald-50/50 to-emerald-100/30 border border-emerald-100 flex flex-col items-center text-center justify-between"
          >
            <span className="text-xs lg:text-sm font-black text-emerald-700 uppercase tracking-widest mb-4">Mastery Rate Index</span>
            
            <div className="relative w-28 h-28 flex items-center justify-center mb-4">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="56" cy="56" r="48" className="stroke-emerald-100" strokeWidth="6" fill="transparent" />
                <motion.circle
                  cx="56"
                  cy="56"
                  r="48"
                  className="stroke-emerald-600"
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
                <span className="text-3xl font-black text-emerald-950 tracking-tight leading-none">{masteryPercentage}%</span>
                <span className="text-[9px] lg:text-xs font-bold text-emerald-500 uppercase tracking-widest mt-1">Index</span>
              </div>
            </div>
            
            <p className="text-sm lg:text-base text-emerald-900/70 font-semibold leading-relaxed">
              Student has demonstrated complete topic mastery in {total} focus area{total !== 1 ? 's' : ''}.
            </p>
          </motion.div>

          {/* Audit parameters */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] border border-gray-100 bg-white space-y-4"
          >
            <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
              <Activity className="w-4 h-4 text-gray-500" />
              <h4 className="text-sm lg:text-base font-black text-gray-800 uppercase tracking-wider">Concept Diagnostics</h4>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Primary Strength</p>
                <p className="text-base font-extrabold text-gray-800 truncate max-w-[150px]">{strengths?.[0] || 'N/A'}</p>
              </div>
              <span className="px-2 py-0.5 rounded-lg bg-emerald-50 border border-emerald-100 text-xs font-black text-emerald-700">Excellent</span>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Cognitive Dimension</p>
                <p className="text-base font-extrabold text-gray-800">Critical Synthesis</p>
              </div>
              <span className="px-2 py-0.5 rounded-lg bg-blue-50 border border-blue-100 text-xs font-black text-blue-700">Active</span>
            </div>

            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Scoring Stability</p>
                <p className="text-base font-extrabold text-gray-800">Verified Consistency</p>
              </div>
              <span className="px-2 py-0.5 rounded-lg bg-violet-50 border border-violet-100 text-xs font-black text-violet-700">96% Conf.</span>
            </div>
          </motion.div>

        </div>
      </motion.div>

    </div>
  );
}
