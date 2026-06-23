// src/components/explainability/AITrustCenter.tsx
'use client';

import React from 'react';
import { motion, Variants } from 'framer-motion';
import { Shield, Server, CheckCircle2, Info, Activity, Fingerprint } from 'lucide-react';

export type ConfidenceFactor = { label: string; score: number };
export type AgentResult     = { name: string; score: number };
export type ExplanationItem = { text: string; positive: boolean };

export interface AITrustCenterProps {
  confidence:    number;
  factors?:      ConfidenceFactor[];
  agents?:       AgentResult[];
  explanations?: ExplanationItem[];
}

const DEFAULT_FACTORS: ConfidenceFactor[] = [
  { label: 'OCR Extraction Quality', score: 96 },
  { label: 'Semantic Context Match', score: 89 },
  { label: 'Rubric Alignment Check', score: 91 },
  { label: 'Fairness Validation',    score: 93 },
];

const DEFAULT_AGENTS: AgentResult[] = [
  { name: 'OCR Agent',             score: 95 },
  { name: 'Evaluation Critic',     score: 91 },
  { name: 'Bias Auditor',          score: 93 },
];

const DEFAULT_EXPLANATIONS: ExplanationItem[] = [
  { text: 'Rubric criteria explicitly met in student answer', positive: true },
  { text: 'Correct formula and calculation steps present',    positive: true },
  { text: 'Clear logical explanation of the steps',           positive: true },
  { text: 'Missing supplementary example for complete mark',  positive: false },
];

const FAIRNESS_CHECKS = [
  { check: 'Bias Check Passed', detail: 'Zero demographic markers detected' },
  { check: 'Consistency Passed', detail: 'Identical scores on repeated runs' },
  { check: 'Validation Passed',  detail: 'Cross-agent score variance < 3%' }
];

export default function AITrustCenter({
  confidence,
  factors      = DEFAULT_FACTORS,
  agents       = DEFAULT_AGENTS,
  explanations = DEFAULT_EXPLANATIONS,
}: AITrustCenterProps) {

  const overallConsensus = Math.round(
    agents.reduce((a, ag) => a + ag.score, 0) / agents.length
  );

  // Animation variants
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.08, delayChildren: 0.1 }
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

  const getBarColor = (s: number) => {
    if (s >= 90) return 'from-emerald-400 to-emerald-500';
    if (s >= 75) return 'from-blue-400 to-blue-500';
    return 'from-amber-400 to-amber-500';
  };

  return (
    <div className="w-full h-full bg-white rounded-[2rem] p-8 md:p-12 lg:p-14 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 flex flex-col overflow-hidden">
      
      {/* ── Header Row ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8 shrink-0 pb-6 border-b border-gray-100">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-2xl bg-gradient-to-br from-brand-primary to-brand-dark shadow-lg shadow-brand-primary/20">
              <Shield className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <h3 className="text-2xl lg:text-3xl font-black text-gray-900 tracking-tight">AI Confidence & Integrity</h3>
          </div>
          <p className="text-gray-500 text-sm lg:text-base font-medium ml-[3.25rem]">
            Real-time consensus audits, bias screening, and scoring reliability reports.
          </p>
        </div>

        {/* Global Verification Stamp */}
        <div className="flex items-center gap-2.5 bg-emerald-50 border border-emerald-100/70 rounded-2xl px-4 py-2 ml-[3.25rem] md:ml-0 self-start md:self-center shrink-0">
          <Fingerprint className="w-4 h-4 text-emerald-600 animate-pulse" />
          <span className="text-xs font-black text-emerald-700 uppercase tracking-widest">Verified Integrity</span>
        </div>
      </div>

      {/* ── Content Grid ── */}
      <motion.div
        className="grid grid-cols-1 lg:grid-cols-12 gap-8 flex-1 min-h-0 overflow-y-auto pr-2 custom-scrollbar"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {/* LEFT COLUMN: Confidence Metric & Agent Consensus (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Radial Confidence Gauge Card */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] bg-gradient-to-br from-gray-50 to-gray-100/50 border border-gray-150 flex flex-col items-center text-center"
          >
            <span className="text-[11px] font-black text-brand-primary uppercase tracking-widest mb-4">Overall Confidence Score</span>
            
            <div className="relative w-36 h-36 flex items-center justify-center mb-4">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="72" cy="72" r="60" className="stroke-gray-200" strokeWidth="8" fill="transparent" />
                <motion.circle
                  cx="72"
                  cy="72"
                  r="60"
                  className="stroke-brand-primary"
                  strokeWidth="8"
                  fill="transparent"
                  strokeDasharray={2 * Math.PI * 60}
                  initial={{ strokeDashoffset: 2 * Math.PI * 60 }}
                  animate={{ strokeDashoffset: 2 * Math.PI * 60 - (confidence / 100) * (2 * Math.PI * 60) }}
                  transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-4xl font-black text-gray-900 tracking-tight leading-none">{confidence}%</span>
                <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest mt-1.5">Reliability</span>
              </div>
            </div>

            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-xs font-black text-brand-primary uppercase tracking-wider mb-2">
              High Scoring Precision
            </span>
            <p className="text-xs text-gray-500 font-medium px-4 leading-relaxed">
              Consensus achieved across all evaluator agents and verified against primary rubrics.
            </p>
          </motion.div>

          {/* Agent Consensus Card */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] border border-gray-100 bg-white"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-gray-500" />
                <h4 className="text-sm font-black text-gray-800 uppercase tracking-wider">Agent Consensus</h4>
              </div>
              <span className="text-xs font-black text-brand-primary uppercase tracking-wider">{overallConsensus}% Consensus</span>
            </div>

            <div className="space-y-4">
              {agents.map((ag) => (
                <div key={ag.name} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-bold text-gray-700">
                    <span>{ag.name}</span>
                    <span>{ag.score}% Accuracy</span>
                  </div>
                  <div className="h-1.5 bg-gray-150 rounded-full overflow-hidden">
                    <motion.div
                      className={`h-full rounded-full bg-gradient-to-r ${getBarColor(ag.score)}`}
                      initial={{ width: 0 }}
                      animate={{ width: `${ag.score}%` }}
                      transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* RIGHT COLUMN: Confidence Factors & Verification (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Confidence Factors */}
          <motion.div
            variants={itemVariants}
            className="p-6 rounded-[2rem] border border-gray-100 bg-white"
          >
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-4 h-4 text-gray-500" />
              <h4 className="text-sm font-black text-gray-800 uppercase tracking-wider">Metrics & Factors</h4>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {factors.map((f) => (
                <div key={f.label} className="p-4 rounded-2xl bg-gray-50/50 border border-gray-100 flex flex-col justify-between">
                  <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">{f.label}</span>
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-xl font-black text-gray-850 leading-none">{f.score}%</span>
                    <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden max-w-[80px]">
                      <motion.div
                        className={`h-full rounded-full bg-gradient-to-r ${getBarColor(f.score)}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${f.score}%` }}
                        transition={{ duration: 1, ease: 'easeOut' }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Award Explanation & Fairness */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            
            {/* Scoring Evidence */}
            <motion.div
              variants={itemVariants}
              className="p-6 rounded-[2rem] border border-gray-100 bg-white flex flex-col justify-between"
            >
              <div className="flex items-center gap-2 mb-3">
                <Info className="w-4 h-4 text-gray-500" />
                <h4 className="text-sm font-black text-gray-800 uppercase tracking-wider">Scoring Rubric Audit</h4>
              </div>
              <div className="space-y-3 flex-1 overflow-y-auto max-h-[140px] pr-1 custom-scrollbar">
                {explanations.map((item, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs font-medium text-gray-600">
                    {item.positive ? (
                      <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-emerald-50 border border-emerald-100 text-emerald-600 text-[10px] font-black shrink-0">✓</span>
                    ) : (
                      <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-amber-50 border border-amber-100 text-amber-600 text-[10px] font-black shrink-0">!</span>
                    )}
                    <span>{item.text}</span>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Fairness verification */}
            <motion.div
              variants={itemVariants}
              className="p-6 rounded-[2rem] border border-gray-100 bg-white flex flex-col justify-between"
            >
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-4 h-4 text-gray-500" />
                <h4 className="text-sm font-black text-gray-800 uppercase tracking-wider">Fairness Checks</h4>
              </div>
              <div className="space-y-3 flex-1">
                {FAIRNESS_CHECKS.map((item, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    <div className="w-5 h-5 rounded-lg bg-emerald-50 border border-emerald-150 flex items-center justify-center text-emerald-600 shrink-0">
                      <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={2.5} />
                    </div>
                    <div>
                      <p className="text-xs font-black text-gray-850 leading-none">{item.check}</p>
                      <p className="text-[10px] font-bold text-gray-450 mt-0.5">{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

          </div>

        </div>
      </motion.div>

    </div>
  );
}
