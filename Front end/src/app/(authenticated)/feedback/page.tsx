'use client';

import React from 'react';
import Image from 'next/image';
import { Sparkles, Target, AlertTriangle, BookOpen, Lightbulb, ArrowRight, Brain } from 'lucide-react';

export default function FeedbackPage() {
  return (
    <div className="p-4 lg:p-6 w-full max-w-full space-y-6">
      
      {/* 1. Hero / AI Welcome Card */}
      <div className="bg-brand-secondary rounded-[24px] overflow-hidden shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col relative min-h-[400px]">
        {/* Full-span Background Illustration */}
        <div className="absolute inset-0 w-full h-full z-0 pointer-events-none opacity-70 overflow-hidden">
          <Image 
            src="/images/feedback-illustration.png" 
            alt="AI Feedback Illustration" 
            fill
            className="object-cover object-right mix-blend-multiply scale-[1.2]"
            priority
          />
        </div>

        <div className="p-10 md:w-2/3 lg:w-1/2 flex flex-col justify-center relative z-10 bg-white/85 backdrop-blur-md h-full min-h-[400px] border-r border-white/50">
          <div className="flex items-center gap-3 mb-6">
             <div className="p-2 bg-brand-primary/10 rounded-xl">
               <Sparkles className="w-5 h-5 text-brand-primary" />
             </div>
             <span className="text-xs font-bold text-brand-primary uppercase tracking-widest">AI Feedback Report</span>
          </div>
          <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-brand-dark mb-6 leading-tight">
            Personalized Insights for <br/>
            <span className="text-brand-accent">Alex Johnson</span>
          </h1>
          <p className="text-gray-600 text-lg max-w-xl leading-relaxed">
            Based on the recent Advanced Physics Midterm, the AI has generated a comprehensive developmental roadmap. Alex shows exceptional mathematical skills but requires targeted conceptual review.
          </p>
          <div className="mt-10">
            <button className="bg-brand-primary text-white font-bold py-4 px-8 rounded-xl hover:bg-opacity-90 active:scale-95 transition-all shadow-[0_10px_30px_rgba(134,183,123,0.3)] flex items-center gap-2 w-fit">
              <BookOpen className="w-5 h-5" />
              Download Study Plan
            </button>
          </div>
        </div>
      </div>

      {/* 2. Main Analytics & Feedback Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Strengths & Weaknesses */}
        <div className="lg:col-span-1 space-y-8">
          
          <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 border-t-4 border-t-brand-primary relative overflow-hidden group">
            <div className="absolute -right-6 -top-6 w-24 h-24 bg-brand-primary/5 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-700" />
            <div className="flex items-center gap-3 mb-8 relative z-10">
              <div className="w-12 h-12 rounded-full bg-[#EEF7E8] flex items-center justify-center">
                <Target className="w-6 h-6 text-brand-primary" />
              </div>
              <h2 className="text-2xl font-bold text-brand-dark">Core Strengths</h2>
            </div>
            <ul className="space-y-6 relative z-10">
              <li className="flex gap-4">
                <div className="mt-1.5 flex-shrink-0 w-2.5 h-2.5 rounded-full bg-brand-primary shadow-[0_0_10px_rgba(134,183,123,0.8)]" />
                <p className="text-gray-600 text-sm leading-relaxed"><strong className="text-brand-dark block text-base mb-1">Mathematical Rigor</strong> Flawless algebraic manipulation across all answered questions.</p>
              </li>
              <li className="flex gap-4">
                <div className="mt-1.5 flex-shrink-0 w-2.5 h-2.5 rounded-full bg-brand-primary shadow-[0_0_10px_rgba(134,183,123,0.8)]" />
                <p className="text-gray-600 text-sm leading-relaxed"><strong className="text-brand-dark block text-base mb-1">Formula Application</strong> Successfully selected the correct formulas for kinematics problems.</p>
              </li>
              <li className="flex gap-4">
                <div className="mt-1.5 flex-shrink-0 w-2.5 h-2.5 rounded-full bg-brand-primary shadow-[0_0_10px_rgba(134,183,123,0.8)]" />
                <p className="text-gray-600 text-sm leading-relaxed"><strong className="text-brand-dark block text-base mb-1">Vector Math</strong> Perfect scores on all graphical vector addition questions.</p>
              </li>
            </ul>
          </div>

          <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 border-t-4 border-t-[#F87171] relative overflow-hidden group">
            <div className="absolute -right-6 -top-6 w-24 h-24 bg-red-500/5 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-700" />
            <div className="flex items-center gap-3 mb-8 relative z-10">
              <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-[#F87171]" />
              </div>
              <h2 className="text-2xl font-bold text-brand-dark">Weak Areas</h2>
            </div>
            <ul className="space-y-6 relative z-10">
              <li className="flex gap-4">
                <div className="mt-1.5 flex-shrink-0 w-2.5 h-2.5 rounded-full bg-[#F87171] shadow-[0_0_10px_rgba(248,113,113,0.8)]" />
                <p className="text-gray-600 text-sm leading-relaxed"><strong className="text-brand-dark block text-base mb-1">Conceptual Friction</strong> Confusing static vs kinetic friction parameters in multi-step equations.</p>
              </li>
              <li className="flex gap-4">
                <div className="mt-1.5 flex-shrink-0 w-2.5 h-2.5 rounded-full bg-[#F87171] shadow-[0_0_10px_rgba(248,113,113,0.8)]" />
                <p className="text-gray-600 text-sm leading-relaxed"><strong className="text-brand-dark block text-base mb-1">Projectile Angles</strong> Forgetting to isolate x and y vectors before applying gravitational constants.</p>
              </li>
            </ul>
          </div>

        </div>

        {/* Right Column: Performance Analysis & Suggestions */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Performance Analysis */}
          <div className="bg-white rounded-[24px] p-10 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 relative overflow-hidden h-fit">
             {/* Decorative watermark */}
             <Brain className="absolute -bottom-16 -right-16 w-96 h-96 text-brand-background opacity-60 z-0 pointer-events-none" />
             
             <div className="relative z-10">
               <h2 className="text-2xl font-bold text-brand-dark mb-8 flex items-center gap-3">
                 <div className="p-2 bg-brand-accent/10 rounded-xl">
                   <Brain className="w-6 h-6 text-brand-accent" />
                 </div>
                 Deep Performance Analysis
               </h2>
               <div className="prose prose-gray max-w-none space-y-6">
                 <p className="text-gray-600 leading-relaxed text-lg">
                   Alex has demonstrated an excellent overall grasp of the material, scoring in the top 15% of the class. The AI analysis indicates that cognitive load is not an issue when dealing with complex mathematical operations. 
                 </p>
                 <p className="text-gray-600 leading-relaxed text-lg">
                   However, a pattern has emerged in questions requiring initial state assumptions. When a problem does not explicitly state which formula to use, Alex occasionally selects parameters that conflict with the physical reality of the problem (e.g., assuming an object is already in motion when calculating friction).
                 </p>
                 <div className="bg-brand-background rounded-2xl p-6 border-l-4 border-brand-accent mt-8 shadow-inner">
                   <h4 className="font-bold text-brand-dark mb-2 text-lg">AI Verdict</h4>
                   <p className="text-gray-600 leading-relaxed">
                     Shift study focus from &quot;solving equations&quot; to &quot;setting up the problem.&quot; Alex needs practice identifying initial conditions from word problems before any math begins.
                   </p>
                 </div>
               </div>
             </div>
          </div>

          {/* Actionable Suggestions & Topics */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            
            {/* Suggestions */}
            <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col h-full">
               <h2 className="text-xl font-bold text-brand-dark mb-6 flex items-center gap-3">
                 <div className="p-2 bg-yellow-50 rounded-xl">
                   <Lightbulb className="w-6 h-6 text-yellow-500" />
                 </div>
                 Actionable Suggestions
               </h2>
               <div className="space-y-4 flex-1">
                 <div className="p-5 bg-yellow-50/50 rounded-xl border border-yellow-100 hover:bg-yellow-50 transition-colors">
                   <p className="text-sm text-gray-700 font-medium leading-relaxed">Draw Free Body Diagrams for every problem, even simple ones, before writing equations.</p>
                 </div>
                 <div className="p-5 bg-brand-background rounded-xl border border-gray-100 hover:bg-gray-50 transition-colors">
                   <p className="text-sm text-gray-700 font-medium leading-relaxed">Review the theoretical definitions of friction coefficients in Chapter 4.</p>
                 </div>
               </div>
            </div>

            {/* Recommended Topics */}
            <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col h-full">
               <h2 className="text-xl font-bold text-brand-dark mb-6 flex items-center gap-3">
                 <div className="p-2 bg-brand-primary/10 rounded-xl">
                   <BookOpen className="w-6 h-6 text-brand-primary" />
                 </div>
                 Recommended Topics
               </h2>
               <div className="space-y-3 flex-1">
                 {['Static vs Kinetic Friction', 'Vector Resolution in 2D', 'Initial Value Problems'].map(topic => (
                   <div key={topic} className="flex items-center justify-between p-4 bg-brand-background hover:bg-brand-surface/20 rounded-xl transition-all cursor-pointer group border border-transparent hover:border-brand-primary/20 hover:shadow-sm">
                     <span className="font-semibold text-brand-dark text-sm">{topic}</span>
                     <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-brand-primary transition-colors transform group-hover:translate-x-1" />
                   </div>
                 ))}
               </div>
               <button className="w-full mt-6 text-sm font-bold text-brand-primary py-3 bg-brand-primary/5 hover:bg-brand-primary/10 rounded-xl transition-colors">
                 Generate Practice Quiz
               </button>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
