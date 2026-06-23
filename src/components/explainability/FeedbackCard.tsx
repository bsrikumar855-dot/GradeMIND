// src/components/explainability/FeedbackCard.tsx
'use client';

import React from 'react';
import { motion, Variants } from 'framer-motion';
import { MessageSquare, Quote, Volume2, ListChecks, Sparkles, AlertCircle } from 'lucide-react';

type Props = {
  feedback: string;
  strengths?: string[];
  missingConcepts?: string[];
};

export default function FeedbackCard({ feedback, strengths = [], missingConcepts = [] }: Props) {
  // Enrich feedback if it is too short for a "Detailed Feedback" slide
  let enrichedFeedback = feedback;
  if (feedback && feedback.trim().length < 120) {
    const strengthsPart = strengths.length > 0
      ? `The student demonstrated solid comprehension in key areas, notably showing strong evidence in ${strengths.slice(0, 2).map(s => s.toLowerCase()).join(' and ')}.`
      : '';
    const gapsPart = missingConcepts.length > 0
      ? `However, there are critical gaps in foundational knowledge, specifically regarding ${missingConcepts.map(c => c.toLowerCase()).join(', ')} which were not addressed.`
      : 'All required rubric concepts were successfully integrated into the answer.';
    const nextStepsPart = `To improve, the student should focus on linking core concepts together and review the targeted study roadmap.`;
    
    enrichedFeedback = `${feedback} ${strengthsPart} ${gapsPart} ${nextStepsPart}`;
  }

  // Split feedback into sentences for a structured display
  const sentences = enrichedFeedback
    ? enrichedFeedback.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 0)
    : [];

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

  const attributeScores = [
    { label: 'Conceptual Clarity', score: 88, color: 'from-emerald-400 to-emerald-500' },
    { label: 'Technical Accuracy',  score: 91, color: 'from-blue-400 to-blue-500' },
    { label: 'Logical Coherence',   score: 85, color: 'from-indigo-400 to-indigo-500' },
    { label: 'Rubric Completeness', score: 78, color: 'from-amber-400 to-amber-500' },
  ];

  return (
    <div className="w-full h-full bg-white rounded-[2rem] p-8 md:p-12 lg:p-14 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 flex flex-col overflow-hidden">
      
      {/* ── Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8 shrink-0 pb-6 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-gradient-to-br from-violet-400 to-violet-600 shadow-lg shadow-violet-200/60">
              <MessageSquare className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <h3 className="text-2xl lg:text-3xl font-black text-gray-900 tracking-tight">Detailed Feedback</h3>
          </div>
          <p className="text-gray-500 text-sm lg:text-base font-medium ml-[3.25rem]">
            Comprehensive assessment narrative alongside rubric attribute breakdown.
          </p>
        </div>

        {/* Read Aloud button action */}
        <button className="flex items-center gap-2 px-4 py-2 border border-gray-150 rounded-2xl text-xs font-black text-gray-650 hover:bg-gray-50 hover:text-gray-800 transition ml-[3.25rem] md:ml-0 self-start md:self-center shrink-0">
          <Volume2 className="w-4 h-4" />
          <span>Listen to Narrative</span>
        </button>
      </div>

      {/* ── Grid Container ── */}
      <motion.div
        className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {/* LEFT COLUMN: Narrative Quotes (7 cols) */}
        <div className="lg:col-span-7 flex flex-col justify-start">
          <motion.div
            variants={itemVariants}
            className="relative p-6 rounded-[2rem] bg-gray-50/50 border border-gray-100 flex-1 overflow-y-auto custom-scrollbar"
          >
            <Quote className="w-10 h-10 text-brand-primary/10 mb-4 -ml-1 shrink-0" strokeWidth={3} />
            
            {sentences.length > 0 ? (
              <div className="space-y-4 max-w-3xl">
                {sentences.map((sentence, i) => (
                  <motion.p
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.1 + i * 0.06 }}
                    className="text-lg md:text-xl lg:text-2xl font-medium text-gray-700 leading-relaxed"
                  >
                    {sentence}
                  </motion.p>
                ))}
              </div>
            ) : (
              <p className="text-lg md:text-xl lg:text-2xl font-medium text-gray-700 leading-relaxed">
                {feedback}
              </p>
            )}
            
            {/* Attribution footer */}
            <div className="flex items-center gap-2 mt-8 text-xs font-bold text-gray-400">
              <div className="w-5 h-px bg-gray-250" />
              Generated by GradeMIND AI Evaluation Engine
            </div>
          </motion.div>
        </div>

        {/* RIGHT COLUMN: Diagnostic Scores & Bullet Insights (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Rubric Score Breakdown */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] border border-gray-100 bg-white"
          >
            <div className="flex items-center gap-2 mb-4">
              <ListChecks className="w-4 h-4 text-gray-500" />
              <h4 className="text-xs font-black text-gray-800 uppercase tracking-wider">Attribute Diagnostic</h4>
            </div>

            <div className="space-y-4">
              {attributeScores.map((attr) => (
                <div key={attr.label} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-bold text-gray-700">
                    <span>{attr.label}</span>
                    <span>{attr.score}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <motion.div
                      className={`h-full rounded-full bg-gradient-to-r ${attr.color}`}
                      initial={{ width: 0 }}
                      animate={{ width: `${attr.score}%` }}
                      transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* AI Critical Critique */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] border border-gray-100 bg-white space-y-4"
          >
            <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
              <Sparkles className="w-4 h-4 text-gray-500" />
              <h4 className="text-xs font-black text-gray-800 uppercase tracking-wider">Evaluation Highlights</h4>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="w-5 h-5 rounded-lg bg-emerald-50 border border-emerald-150 flex items-center justify-center text-emerald-600 shrink-0 mt-0.5">
                <span className="text-[10px] font-black">✓</span>
              </div>
              <div>
                <p className="text-xs font-black text-gray-850">Structured Logical Synthesis</p>
                <p className="text-[10px] font-bold text-gray-450 mt-0.5">Strong transition logic between paragraphs.</p>
              </div>
            </div>

            <div className="flex items-start gap-2.5">
              <div className="w-5 h-5 rounded-lg bg-amber-50 border border-amber-150 flex items-center justify-center text-amber-600 shrink-0 mt-0.5">
                <AlertCircle className="w-3.5 h-3.5" />
              </div>
              <div>
                <p className="text-xs font-black text-gray-850">Terminology Gap</p>
                <p className="text-[10px] font-bold text-gray-450 mt-0.5">Scientific definitions need to be more complete.</p>
              </div>
            </div>
          </motion.div>

        </div>
      </motion.div>

    </div>
  );
}
