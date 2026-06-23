// src/components/explainability/EvaluationSummary.tsx
'use client';

import React from 'react';
import { motion, Variants } from 'framer-motion';
import { User, Calendar, Award, CheckCircle2 } from 'lucide-react';

type Props = {
  data: {
    score: number;
    max_score: number;
    question: string;
    student_name: string;
    evaluation_date: string;
  };
};

export default function EvaluationSummary({ data }: Props) {
  const { score, max_score, question, student_name, evaluation_date } = data;
  const percentage = Math.round((score / max_score) * 100);

  // Determine grade badge & status text
  let statusText = 'Needs Focus';
  let statusColor = 'text-rose-600 bg-rose-50 border-rose-100';

  if (percentage >= 85) {
    statusText = 'Excellent Performance';
    statusColor = 'text-emerald-700 bg-emerald-50 border-emerald-100';
  } else if (percentage >= 70) {
    statusText = 'Good Comprehension';
    statusColor = 'text-blue-700 bg-blue-50 border-blue-100';
  }

  // Framer Motion Animation Variants
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.1 }
    }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 15 },
    show: {
      opacity: 1,
      y: 0,
      transition: { type: 'spring', stiffness: 350, damping: 25 }
    }
  };

  // SVG Radial Ring dimensions
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <motion.div
      className="flex flex-col justify-center py-2 text-left"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* ── Topic Badge ── */}
      <motion.div variants={itemVariants} className="mb-4">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-xs font-black text-brand-primary uppercase tracking-wider">
          <Award className="w-3.5 h-3.5" />
          Academic Evaluation
        </span>
      </motion.div>

      {/* ── Question Header ── */}
      <motion.h1
        variants={itemVariants}
        className="text-3xl md:text-4xl lg:text-5xl font-black text-gray-900 mb-6 leading-tight tracking-tight max-w-2xl"
      >
        {question}
      </motion.h1>

      {/* ── Metadata Grid ── */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8 max-w-lg">
        {/* Student Card */}
        <div className="flex items-center gap-3.5 p-4 rounded-2xl bg-gray-50 border border-gray-100 hover:border-gray-200 transition-colors">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-400 to-blue-600 shadow-md shadow-blue-100 flex items-center justify-center shrink-0">
            <User className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Student Name</p>
            <p className="text-base font-extrabold text-gray-800 truncate">{student_name}</p>
          </div>
        </div>

        {/* Date Card */}
        <div className="flex items-center gap-3.5 p-4 rounded-2xl bg-gray-50 border border-gray-100 hover:border-gray-200 transition-colors">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-400 to-violet-600 shadow-md shadow-violet-100 flex items-center justify-center shrink-0">
            <Calendar className="w-4 h-4 text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Evaluation Date</p>
            <p className="text-base font-extrabold text-gray-800 truncate">{evaluation_date}</p>
          </div>
        </div>
      </motion.div>

      {/* ── Score Dashboard Card ── */}
      <motion.div
        variants={itemVariants}
        className="flex flex-col sm:flex-row items-center gap-6 p-6 rounded-[2rem] bg-gradient-to-br from-gray-50 to-gray-100/50 border border-gray-150 max-w-xl shadow-sm relative overflow-hidden"
      >
        {/* Radial Progress Ring */}
        <div className="relative w-28 h-28 flex items-center justify-center shrink-0">
          <svg className="w-full h-full transform -rotate-90">
            {/* Background Circle */}
            <circle
              cx="56"
              cy="56"
              r={radius}
              className="stroke-gray-200"
              strokeWidth="7"
              fill="transparent"
            />
            {/* Foreground Circle */}
            <motion.circle
              cx="56"
              cy="56"
              r={radius}
              className="stroke-brand-primary"
              strokeWidth="7"
              fill="transparent"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset }}
              transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
              strokeLinecap="round"
            />
          </svg>
          {/* Central Percentage */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-black text-gray-850 tracking-tight leading-none">{percentage}%</span>
            <span className="text-[9px] font-bold text-gray-450 uppercase tracking-widest mt-0.5">Score</span>
          </div>
        </div>

        {/* Text Metrics */}
        <div className="flex-1 text-center sm:text-left min-w-0">
          <p className="text-[11px] font-black text-brand-primary uppercase tracking-widest mb-1.5">Overall Grade</p>
          <div className="flex flex-wrap items-baseline justify-center sm:justify-start gap-2 mb-2">
            <span className="text-4xl font-black text-gray-900 leading-none">{score}</span>
            <span className="text-lg font-bold text-gray-400">/ {max_score} points</span>
          </div>
          
          <div className="flex items-center justify-center sm:justify-start gap-2.5 mt-2.5">
            <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-xl text-xs font-extrabold border ${statusColor}`}>
              <CheckCircle2 className="w-3.5 h-3.5" />
              {statusText}
            </span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
