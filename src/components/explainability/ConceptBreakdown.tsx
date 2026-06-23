// src/components/explainability/ConceptBreakdown.tsx
import React from 'react';
import { motion, Variants } from 'framer-motion';
import { CheckCircle2, AlertCircle, XCircle } from 'lucide-react';

type Concept = {
  name: string;
  score: number;
  max_score: number;
};

type Props = {
  concepts: Concept[];
};

export default function ConceptBreakdown({ concepts }: Props) {
  // Ultra-smooth animation variants
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.1 }
    }
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, x: -10 },
    show: { 
      opacity: 1, 
      x: 0,
      transition: { type: 'spring', stiffness: 400, damping: 30 }
    }
  };

  return (
    <div className="w-full h-full bg-white rounded-[2rem] p-8 md:p-12 lg:p-16 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-gray-100 flex flex-col overflow-hidden">
      
      {/* Premium Header */}
      <div className="flex flex-col mb-12 shrink-0 border-b border-gray-100 pb-8">
        <h3 className="text-3xl lg:text-4xl font-black text-gray-900 tracking-tight leading-none mb-3">Concept Mastery</h3>
        <p className="text-gray-500 text-base font-medium">A granular analysis of foundational knowledge and topic comprehension.</p>
      </div>
      
      {/* Minimalist Ledger List */}
      <motion.div 
        className="flex-1 flex flex-col justify-start overflow-y-auto pr-4 custom-scrollbar space-y-1"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {concepts.map((c) => {
          const pct = Math.round((c.score / c.max_score) * 100);
          
          let gradientColor = '';
          let StatusIcon = null;
          let iconColor = '';
          
          if (pct >= 80) {
            gradientColor = 'from-emerald-400 to-emerald-500';
            StatusIcon = CheckCircle2;
            iconColor = 'text-emerald-500';
          } else if (pct >= 50) {
            gradientColor = 'from-amber-400 to-amber-500';
            StatusIcon = AlertCircle;
            iconColor = 'text-amber-500';
          } else {
            gradientColor = 'from-rose-400 to-rose-500';
            StatusIcon = XCircle;
            iconColor = 'text-rose-500';
          }

          return (
            <motion.div 
              key={c.name} 
              variants={itemVariants}
              className="w-full group p-4 rounded-2xl hover:bg-gray-50 transition-colors duration-300"
            >
              <div className="flex items-center justify-between mb-4">
                
                {/* Left: Icon & Name */}
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-xl bg-white shadow-sm border border-gray-100 ${iconColor}`}>
                    <StatusIcon className="w-5 h-5" strokeWidth={2.5} />
                  </div>
                  <span className="text-lg lg:text-xl font-bold text-gray-800 tracking-tight">{c.name}</span>
                </div>
                
                {/* Right: Score Metrics */}
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-black text-gray-900 leading-none">{c.score}</span>
                  <span className="text-sm font-bold text-gray-400">/ {c.max_score}</span>
                </div>

              </div>
              
              {/* Ultra-thin Glowing Progress Bar */}
              <div className="w-full pl-[3.25rem]">
                <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-visible relative">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
                    className={`bg-gradient-to-r ${gradientColor} h-full rounded-full relative z-10`}
                  >
                    {/* Glowing Thumb */}
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-[0_0_10px_rgba(0,0,0,0.2)] border border-gray-100/50" />
                  </motion.div>
                </div>
              </div>

            </motion.div>
          );
        })}
      </motion.div>

    </div>
  );
}
