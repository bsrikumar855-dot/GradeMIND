'use client';

import React from 'react';
import { 
  PieChart, Pie, Cell, 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
import { Award, Target, Brain, AlertTriangle, Lightbulb } from 'lucide-react';

const pieData = [
  { name: 'Correct', value: 7, color: '#86B77B' },
  { name: 'Partial', value: 2, color: '#5B8DEF' },
  { name: 'Incorrect', value: 1, color: '#F87171' },
];

const barData = [
  { question: 'Q1', marks: 10, max: 10 },
  { question: 'Q2', marks: 8, max: 10 },
  { question: 'Q3', marks: 10, max: 10 },
  { question: 'Q4', marks: 5, max: 10 },
  { question: 'Q5', marks: 10, max: 10 },
  { question: 'Q6', marks: 9, max: 10 },
  { question: 'Q7', marks: 10, max: 10 },
  { question: 'Q8', marks: 0, max: 10 },
  { question: 'Q9', marks: 4, max: 10 },
  { question: 'Q10', marks: 10, max: 10 },
];

const questionTable = [
  { q: 'Q1. Newton\'s First Law', marks: '10/10', feedback: 'Perfect explanation with correct real-world example.', status: 'Correct' },
  { q: 'Q2. Kinematics Equation', marks: '8/10', feedback: 'Correct formula used, but minor calculation error in the final step.', status: 'Partial' },
  { q: 'Q3. Vector Addition', marks: '10/10', feedback: 'Excellent graphical and mathematical representation.', status: 'Correct' },
  { q: 'Q4. Projectile Motion', marks: '5/10', feedback: 'Failed to account for the angle of projection. Review chapter 4.', status: 'Partial' },
  { q: 'Q8. Friction Coefficient', marks: '0/10', feedback: 'Incorrect assumption about kinetic vs static friction. Completely missed the core concept.', status: 'Incorrect' },
];

export default function ResultsDashboard() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      
      {/* 1. Student Summary Banner */}
      <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col lg:flex-row justify-between items-center gap-8">
         {/* Name & Subject */}
         <div className="flex items-center gap-6">
            <div className="w-20 h-20 bg-brand-surface rounded-full flex items-center justify-center text-brand-dark text-2xl font-bold">
              AJ
            </div>
            <div>
              <h1 className="text-3xl font-bold text-brand-dark">Alex Johnson</h1>
              <p className="text-gray-500 font-medium mt-1">Advanced Physics Midterm • ID: PHY-1042</p>
            </div>
         </div>
         {/* Metrics */}
         <div className="flex flex-wrap lg:flex-nowrap gap-4 w-full lg:w-auto">
            <div className="bg-brand-background px-6 py-4 rounded-2xl border border-gray-100 flex-1 lg:flex-none">
              <p className="text-sm font-semibold text-gray-500 mb-1">Total Marks</p>
              <p className="text-2xl font-bold text-brand-dark">86 <span className="text-sm text-gray-400 font-medium">/ 100</span></p>
            </div>
            <div className="bg-brand-background px-6 py-4 rounded-2xl border border-gray-100 flex-1 lg:flex-none">
              <p className="text-sm font-semibold text-gray-500 mb-1">Percentage</p>
              <p className="text-2xl font-bold text-brand-accent">86%</p>
            </div>
            <div className="bg-brand-primary px-8 py-4 rounded-2xl shadow-[0_10px_30px_rgba(134,183,123,0.3)] flex-1 lg:flex-none flex items-center justify-between gap-6 min-w-[160px]">
              <div>
                <p className="text-sm font-semibold text-white/80 mb-1">Grade</p>
                <p className="text-4xl font-extrabold text-white">A</p>
              </div>
              <Award className="w-12 h-12 text-white/50" />
            </div>
         </div>
      </div>

      {/* 2. Analytics Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left: Charts Column */}
        <div className="lg:col-span-2 space-y-8">
           
           {/* Bar Chart: Question vs Marks */}
           <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
             <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-brand-dark">Question vs Marks</h2>
             </div>
             <div className="h-[300px] w-full">
               <ResponsiveContainer width="100%" height="100%">
                 <BarChart data={barData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                   <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F3F4F6" />
                   <XAxis dataKey="question" axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} dy={10} />
                   <YAxis axisLine={false} tickLine={false} tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                   <Tooltip 
                     cursor={{ fill: '#EEF7E8' }}
                     contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(47,90,58,0.1)' }}
                   />
                   <Bar dataKey="marks" fill="#86B77B" radius={[6, 6, 0, 0]} maxBarSize={40} />
                 </BarChart>
               </ResponsiveContainer>
             </div>
           </div>

           {/* Distribution & Performance Summary (Split Row) */}
           <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {/* Pie Chart */}
              <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col items-center">
                 <h2 className="text-xl font-bold text-brand-dark mb-2 w-full text-left">Accuracy Distribution</h2>
                 <div className="h-[220px] w-full relative">
                   <ResponsiveContainer width="100%" height="100%">
                     <PieChart>
                       <Pie
                         data={pieData}
                         innerRadius={65}
                         outerRadius={85}
                         paddingAngle={5}
                         dataKey="value"
                         stroke="none"
                       >
                         {pieData.map((entry, index) => (
                           <Cell key={`cell-${index}`} fill={entry.color} />
                         ))}
                       </Pie>
                       <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }} />
                     </PieChart>
                   </ResponsiveContainer>
                   <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                     <span className="text-3xl font-extrabold text-brand-dark">70%</span>
                   </div>
                 </div>
                 {/* Legend */}
                 <div className="flex gap-4 mt-4 w-full justify-center">
                    {pieData.map(item => (
                      <div key={item.name} className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                        <span className="text-sm font-medium text-gray-500">{item.name}</span>
                      </div>
                    ))}
                 </div>
              </div>

              {/* Strengths / Weaknesses */}
              <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
                 <h2 className="text-xl font-bold text-brand-dark mb-6">Performance Profile</h2>
                 
                 <div className="space-y-6">
                   <div>
                     <div className="flex items-center gap-2 mb-3">
                       <Target className="w-5 h-5 text-brand-primary" />
                       <h3 className="font-semibold text-brand-dark">Strengths</h3>
                     </div>
                     <div className="flex flex-wrap gap-2">
                       <span className="px-3 py-1.5 bg-[#EEF7E8] text-brand-dark rounded-lg text-sm font-semibold border border-brand-primary/20">Classical Mechanics</span>
                       <span className="px-3 py-1.5 bg-[#EEF7E8] text-brand-dark rounded-lg text-sm font-semibold border border-brand-primary/20">Vector Math</span>
                     </div>
                   </div>
                   
                   <div>
                     <div className="flex items-center gap-2 mb-3 mt-8">
                       <AlertTriangle className="w-5 h-5 text-[#F87171]" />
                       <h3 className="font-semibold text-brand-dark">Weak Areas</h3>
                     </div>
                     <div className="flex flex-wrap gap-2">
                       <span className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-sm font-semibold border border-red-200">Friction Forces</span>
                       <span className="px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-sm font-semibold border border-red-200">Projectile Angles</span>
                     </div>
                   </div>
                 </div>
              </div>
           </div>

        </div>

        {/* Right: AI Insights */}
        <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-3 bg-brand-accent/10 rounded-xl">
              <Brain className="w-6 h-6 text-brand-accent" />
            </div>
            <h2 className="text-xl font-bold text-brand-dark">AI Insights</h2>
          </div>
          
          <div className="flex-1 space-y-6">
            <div className="bg-brand-background rounded-2xl p-6 border border-brand-accent/20 relative overflow-hidden group hover:border-brand-accent/50 transition-colors">
              <div className="absolute top-0 left-0 w-1.5 h-full bg-brand-accent" />
              <h4 className="font-bold text-brand-dark flex items-center gap-2 mb-3">
                <Lightbulb className="w-5 h-5 text-brand-accent" /> Conceptual Gap Detected
              </h4>
              <p className="text-sm text-gray-600 leading-relaxed">
                Alex consistently applies equations correctly but struggles with the initial physical assumptions, specifically mixing up kinetic and static friction states in multi-part problems (Q8, Q9).
              </p>
            </div>

            <div className="bg-brand-background rounded-2xl p-6 border border-brand-primary/20 relative overflow-hidden group hover:border-brand-primary/50 transition-colors">
              <div className="absolute top-0 left-0 w-1.5 h-full bg-brand-primary" />
              <h4 className="font-bold text-brand-dark flex items-center gap-2 mb-3">
                <Lightbulb className="w-5 h-5 text-brand-primary" /> Mathematical Rigor
              </h4>
              <p className="text-sm text-gray-600 leading-relaxed">
                Mathematical execution is exceptional. When the correct formula is selected, calculations are flawless. Recommending conceptual theory review rather than math practice.
              </p>
            </div>
          </div>

          <div className="flex gap-4 mt-8">
            <button className="flex-1 bg-brand-background text-brand-dark font-bold py-4 rounded-xl border border-gray-200 hover:bg-gray-100 transition-colors">
              Download Full PDF Report
            </button>
            <button onClick={() => window.location.href='/feedback'} className="flex-1 bg-brand-primary text-white font-bold py-4 rounded-xl hover:bg-opacity-90 active:scale-95 transition-all shadow-[0_10px_30px_rgba(134,183,123,0.3)]">
              View Detailed Feedback
            </button>
          </div>
        </div>

      </div>

      {/* 3. Question Wise Table */}
      <div className="bg-white rounded-[24px] p-8 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
        <h2 className="text-xl font-bold text-brand-dark mb-6">Question Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b-2 border-gray-100">
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider w-1/4">Question</th>
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider w-32">Status</th>
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider w-24">Marks</th>
                <th className="pb-4 text-xs font-bold text-gray-400 uppercase tracking-wider">AI Feedback</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {questionTable.map((row, idx) => (
                <tr key={idx} className="hover:bg-brand-background/50 transition-colors">
                  <td className="py-5 pr-4 font-semibold text-brand-dark">{row.q}</td>
                  <td className="py-5">
                    <span className={`px-3 py-1.5 rounded-full text-xs font-bold ${
                      row.status === 'Correct' ? 'bg-[#EEF7E8] text-[#2F5A3A]' :
                      row.status === 'Partial' ? 'bg-blue-50 text-blue-700' :
                      'bg-red-50 text-red-700'
                    }`}>
                      {row.status}
                    </span>
                  </td>
                  <td className="py-5 font-bold text-brand-dark">{row.marks}</td>
                  <td className="py-5 text-sm text-gray-600 leading-relaxed pr-4">{row.feedback}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
