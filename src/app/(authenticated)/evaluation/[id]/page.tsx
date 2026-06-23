'use client';
import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import { useRouter, useParams, useSearchParams } from 'next/navigation';
import { EvaluationService } from '@/services/evaluation.service';
import EvaluationSummary from '@/components/explainability/EvaluationSummary';
import AITrustCenter from '@/components/explainability/AITrustCenter';
import ConceptBreakdown from '@/components/explainability/ConceptBreakdown';
import StrengthsCard from '@/components/explainability/StrengthsCard';
import MissingConceptsCard from '@/components/explainability/MissingConceptsCard';
import SuggestionsCard from '@/components/explainability/SuggestionsCard';
import FeedbackCard from '@/components/explainability/FeedbackCard';
import ConceptInsights from '@/components/explainability/ConceptInsights';
import AIRecommendations from '@/components/explainability/AIRecommendations';
import EvidenceViewer from '@/components/explainability/evidence/EvidenceViewer';
import { MOCK_FULL_TEXT, MOCK_CONCEPT_EVIDENCE } from '@/components/explainability/evidence/mockData';
import { cn } from '@/utils/cn';
import { motion, AnimatePresence, Variants } from 'framer-motion';
import {
  BarChart3,
  Shield,
  Brain,
  Sparkles,
  AlertTriangle,
  Lightbulb,
  MessageSquare,
  Target,
  Zap,
} from 'lucide-react';

const STEP_LABELS = [
  'Summary',
  'Confidence',
  'Concepts',
  'Evidence',
  'Strengths',
  'Missing',
  'Suggestions',
  'Feedback',
  'Insights',
  'Recommendations',
];

const STEP_ICONS = [
  <BarChart3 key="s" className="size-4 text-brand-primary" />,
  <Shield key="c" className="size-4 text-brand-primary" />,
  <Brain key="co" className="size-4 text-brand-primary" />,
  <Target key="ev" className="size-4 text-brand-primary" />,
  <Sparkles key="st" className="size-4 text-brand-primary" />,
  <AlertTriangle key="m" className="size-4 text-amber-500" />,
  <Lightbulb key="su" className="size-4 text-brand-primary" />,
  <MessageSquare key="f" className="size-4 text-brand-primary" />,
  <Target key="i" className="size-4 text-brand-primary" />,
  <Zap key="r" className="size-4 text-brand-primary" />,
];

const STEP_DESCRIPTIONS = [
  'Score overview & key metrics',
  'AI confidence & trust score',
  'Concept-level breakdown',
  'Interactive evidence mapping',
  'What went well',
  'Areas to improve',
  'Actionable suggestions',
  'Detailed AI feedback',
  'Learning gap analysis',
  'AI-powered recommendations',
];

type EvaluationData = {
  score: number;
  max_score: number;
  confidence: number;
  question: string;
  student_name: string;
  evaluation_date: string;
  concepts: Array<{
    name: string;
    score: number;
    max_score: number;
  }>;
  strengths: string[];
  missing_concepts: string[];
  suggestions: string[];
  feedback: string;
};

export default function EvaluationPage() {
  const router = useRouter();
  const { id } = useParams() as { id: string };
  const searchParams = useSearchParams();
  const initialStep = STEP_LABELS.findIndex((label) => label.toLowerCase() === searchParams.get('step')?.toLowerCase());
  const [data, setData] = useState<EvaluationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(initialStep >= 0 ? initialStep : 0);
  const [direction, setDirection] = useState(1);

  const totalSteps = STEP_LABELS.length;

  useEffect(() => {
    if (!id) {
      setLoading(false);
      return;
    }

    let isMounted = true;

    EvaluationService.getEvaluationById(id)
      .then((res) => {
        if (isMounted) {
          setData(res);
        }
      })
      .catch(() => {
        if (isMounted) {
          setData(null);
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [id]);

  const goNext = () => {
    if (step < totalSteps - 1) {
      setDirection(1);
      setStep(step + 1);
    }
  };

  const goPrev = () => {
    if (step > 0) {
      setDirection(-1);
      setStep(step - 1);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
        <Image src="/images/college%20project-amico.svg" alt="empty" width={160} height={160} className="w-40 h-40 object-contain" />
        <p className="text-base text-gray-800">No evaluation data available yet.</p>
        <button
          onClick={() => router.push('/dashboard')}
          className="px-4 py-2 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-brand-dark transition"
        >
          Go to Dashboard
        </button>
      </div>
    );
  }

  const stepCards: React.ReactNode[] = [
    // 0 — Summary
    <div key="summary" className="w-full h-full bg-white rounded-[2rem] p-8 md:p-12 lg:p-16 shadow-[0_24px_70px_rgba(47,90,58,0.08)] border border-gray-100 flex flex-col-reverse md:flex-row items-center justify-between gap-12 lg:gap-16 xl:gap-24 overflow-hidden">
      <div className="flex-1 w-full">
        <EvaluationSummary data={data} />
      </div>
      <Image src="/images/Grades-cuate.svg" alt="hero" width={600} height={600} className="w-80 h-80 md:w-[28rem] md:h-[28rem] lg:w-[36rem] lg:h-[36rem] xl:w-[42rem] xl:h-[42rem] object-contain flex-shrink-0" />
    </div>,

    // 1 — Confidence
    <div key="confidence" className="w-full h-full">
      <AITrustCenter confidence={data.confidence} />
    </div>,

    // 2 — Concept Breakdown
    <div key="concepts" className="w-full h-full">
      <ConceptBreakdown concepts={data.concepts} />
    </div>,

    // 3 — Evidence
    <div key="evidence" className="w-full h-full">
      <EvidenceViewer fullText={MOCK_FULL_TEXT} concepts={MOCK_CONCEPT_EVIDENCE} />
    </div>,

    // 4 — Strengths
    <div key="strengths" className="w-full h-full">
      <StrengthsCard strengths={data.strengths} />
    </div>,

    // 5 — Missing Concepts
    <div key="missing" className="w-full h-full">
      <MissingConceptsCard missing={data.missing_concepts} />
    </div>,

    // 6 — Suggestions
    <div key="suggestions" className="w-full h-full">
      <SuggestionsCard suggestions={data.suggestions} />
    </div>,

    // 7 — Feedback
    <div key="feedback" className="w-full h-full">
      <FeedbackCard feedback={data.feedback} strengths={data.strengths} missingConcepts={data.missing_concepts} />
    </div>,

    // 8 — Concept Insights
    <div key="insights" className="w-full h-full">
      <ConceptInsights concepts={data.concepts} />
    </div>,

    // 9 — AI Recommendations
    <div key="recommendations" className="w-full h-full">
      <AIRecommendations missingConcepts={data.missing_concepts} score={data.score} max_score={data.max_score} />
    </div>,
  ];

  const slideVariants: Variants = {
    enter: (dir: number) => ({
      x: dir > 0 ? '30%' : '-30%',
      opacity: 0,
      scale: 0.98,
    }),
    center: {
      x: 0,
      opacity: 1,
      scale: 1,
      transition: {
        x: { duration: 0.5, ease: [0.25, 0.1, 0.25, 1] },
        opacity: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] },
        scale: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] },
      },
    },
    exit: (dir: number) => ({
      x: dir > 0 ? '-15%' : '15%',
      opacity: 0,
      scale: 0.98,
      transition: {
        x: { duration: 0.35, ease: [0.55, 0, 1, 0.45] },
        opacity: { duration: 0.25, ease: [0.55, 0, 1, 0.45] },
        scale: { duration: 0.25, ease: [0.55, 0, 1, 0.45] },
      },
    }),
  };

  // Build the stacked preview cards for the nav panel
  const getVisibleSteps = () => {
    const visible: number[] = [];
    for (let i = step; i < Math.min(step + 3, totalSteps); i++) {
      visible.push(i);
    }
    return visible;
  };

  return (
    <div className="flex flex-1 flex-col w-full h-[calc(100vh-96px)] p-6 lg:p-8 xl:p-10 gap-5 overflow-hidden bg-brand-background">
      {/* Back Button */}
      <button
        onClick={() => router.push('/dashboard')}
        className="flex w-fit items-center gap-2.5 text-xl lg:text-2xl font-bold text-brand-dark hover:text-brand-primary transition-colors duration-200"
      >
        <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Dashboard
      </button>

      {/* Main Content: Card + Stacked Nav */}
      <div className="flex flex-1 gap-8 min-h-0 overflow-hidden">

        {/* Left — Active card with slide animation */}
        <div className="relative flex-1 overflow-hidden min-h-0">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={step}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              className="h-full will-change-transform"
            >
              {stepCards[step]}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Right — Stacked display cards nav */}
        <div className="hidden xl:flex flex-col items-center justify-center w-[340px] shrink-0">
          <div className="grid [grid-template-areas:'stack'] place-items-center w-full">
            {getVisibleSteps().map((stepIdx, offset) => {
              const isActive = stepIdx === step;
              return (
                <motion.button
                  key={stepIdx}
                  onClick={() => {
                    setDirection(stepIdx > step ? 1 : -1);
                    setStep(stepIdx);
                  }}
                  whileHover={offset === 0 ? { y: -6, scale: 1.02 } : offset === 1 ? { y: -4 } : { y: -2 }}
                  whileTap={{ scale: 0.98 }}
                  transition={{ type: 'spring', stiffness: 260, damping: 22 }}
                  className={cn(
                    "relative flex h-32 w-[20rem] select-none flex-col justify-between rounded-xl border-2 px-4 py-3 transition-colors transition-shadow duration-300 [grid-area:stack] cursor-pointer",
                    "after:absolute after:-right-1 after:top-[-5%] after:h-[110%] after:w-[18rem] after:bg-gradient-to-l after:from-brand-background after:to-transparent after:content-['']",
                    offset === 0 && isActive && "-skew-y-[8deg] border-brand-primary/40 bg-white shadow-lg hover:shadow-xl z-30",
                    offset === 0 && !isActive && "-skew-y-[8deg] border-brand-surface/60 bg-white/80 hover:border-brand-primary/30 hover:bg-white z-30",
                    offset === 1 && "-skew-y-[8deg] translate-x-10 translate-y-8 border-brand-surface/40 bg-white/60 backdrop-blur-sm z-20 before:absolute before:inset-0 before:rounded-xl before:bg-brand-background/40 before:content-[''] hover:before:opacity-0 before:transition-opacity before:duration-500 grayscale-[80%] hover:grayscale-0",
                    offset === 2 && "-skew-y-[8deg] translate-x-20 translate-y-16 border-brand-surface/30 bg-white/40 backdrop-blur-sm z-10 before:absolute before:inset-0 before:rounded-xl before:bg-brand-background/60 before:content-[''] hover:before:opacity-0 before:transition-opacity before:duration-500 grayscale-[100%] hover:grayscale-0",
                  )}
                >
                  <div className="flex items-center gap-2 relative z-10">
                    <span className="inline-block rounded-full bg-brand-secondary p-1.5">
                      {STEP_ICONS[stepIdx]}
                    </span>
                    <p className={cn(
                      "text-base font-semibold",
                      isActive ? "text-brand-primary" : "text-brand-dark"
                    )}>
                      {STEP_LABELS[stepIdx]}
                    </p>
                  </div>
                  <p className="text-sm text-gray-600 relative z-10">{STEP_DESCRIPTIONS[stepIdx]}</p>
                  <p className="text-xs text-gray-400 relative z-10">Step {stepIdx + 1} of {totalSteps}</p>
                </motion.button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Step Progress Bar + Nav Buttons */}
      <div className="flex items-center gap-6 pt-2 pb-2">
        <button
          onClick={goPrev}
          disabled={step === 0}
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-lg font-bold bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all shrink-0"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" /></svg>
          Previous
        </button>

        <div className="flex items-center gap-2 flex-1">
          {STEP_LABELS.map((label, i) => (
            <button
              key={label}
              onClick={() => {
                setDirection(i > step ? 1 : -1);
                setStep(i);
              }}
              className={cn(
                "flex-1 h-3 lg:h-4 rounded-full transition-all duration-300 ease-out cursor-pointer hover:scale-y-125",
                i <= step ? 'bg-brand-primary' : 'bg-gray-200',
                i === step && 'ring-2 ring-brand-primary/30 ring-offset-1'
              )}
              title={label}
            />
          ))}
        </div>

        <p className="text-base font-bold text-brand-dark/70 shrink-0 min-w-[120px] text-center">
          {step + 1} / {totalSteps}
        </p>

        <button
          onClick={goNext}
          disabled={step === totalSteps - 1}
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-lg font-bold bg-brand-primary text-white hover:bg-brand-dark disabled:opacity-40 disabled:cursor-not-allowed transition-all shrink-0"
        >
          Next
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" /></svg>
        </button>
      </div>
    </div>
  );
}
