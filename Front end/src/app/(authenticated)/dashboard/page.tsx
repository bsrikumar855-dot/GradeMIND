'use client';

import React from 'react';
import Link from 'next/link';
import { AnalyticsCard } from '@/components/charts/analytics-card';

// Mock Data
const recentEvaluations = [
  { id: 'EV-1042', subject: 'Mathematics 101', date: 'Today, 09:41 AM', students: 45, status: 'Completed', score: '82% Avg' },
  { id: 'EV-1041', subject: 'Physics - Midterm', date: 'Yesterday, 14:20', students: 38, status: 'Completed', score: '76% Avg' },
  { id: 'EV-1040', subject: 'Chemistry Lab', date: 'Oct 12, 11:00 AM', students: 22, status: 'Processing', score: '--' },
  { id: 'EV-1039', subject: 'Biology Quiz', date: 'Oct 10, 16:15 PM', students: 40, status: 'Completed', score: '88% Avg' },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      
      {/* 1. KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <AnalyticsCard
          title="Total Exams"
          value="142"
          trend={{ value: '12', isPositive: true, label: 'last month' }}
          icon={<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>}
        />
        <AnalyticsCard
          title="Students Evaluated"
          value="3,284"
          trend={{ value: '14.2%', isPositive: true, label: 'last month' }}
          icon={<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>}
        />
        <AnalyticsCard
          title="AI Accuracy"
          value="99.4%"
          variant="primary"
          trend={{ value: '0.2%', isPositive: true }}
          icon={<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <AnalyticsCard
          title="Reports Generated"
          value="286"
          variant="accent"
          trend={{ value: '42', isPositive: true, label: 'this week' }}
          icon={<svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" /></svg>}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* 2. Left Column - Charts & Activity */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Evaluation Activity Chart (Mock) */}
          <div className="bg-white rounded-2xl p-6 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-brand-dark">Evaluation Activity</h2>
              <select className="bg-brand-background border border-gray-200 text-sm rounded-lg px-3 py-1.5 outline-none focus:border-brand-primary text-gray-600">
                <option>Last 7 Days</option>
                <option>Last 30 Days</option>
              </select>
            </div>
            
            {/* CSS Bar Chart Mockup to maintain standard Next.js dependencies */}
            <div className="h-64 flex items-end justify-between gap-2 pb-6 border-b border-gray-100 relative">
              {/* Y-Axis lines */}
              <div className="absolute w-full border-t border-dashed border-gray-200 top-0"></div>
              <div className="absolute w-full border-t border-dashed border-gray-200 top-1/2"></div>
              
              {[40, 70, 45, 90, 65, 80, 55].map((height, i) => (
                <div key={i} className="w-full flex justify-center group relative z-10">
                  <div 
                    className="w-12 bg-brand-surface rounded-t-lg relative transition-all duration-300 group-hover:bg-brand-primary cursor-pointer"
                    style={{ height: `${height}%` }}
                  >
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-brand-dark text-white text-xs py-1 px-2 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                      {height * 12}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-4 text-xs font-medium text-gray-400">
              <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun</span>
            </div>
          </div>

          {/* Recent Evaluations Table */}
          <div className="bg-white rounded-2xl p-6 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-brand-dark">Recent Evaluations</h2>
              <button className="text-brand-primary text-sm font-medium hover:underline">View All</button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="pb-3 text-sm font-semibold text-gray-400">ID / Subject</th>
                    <th className="pb-3 text-sm font-semibold text-gray-400">Date</th>
                    <th className="pb-3 text-sm font-semibold text-gray-400">Students</th>
                    <th className="pb-3 text-sm font-semibold text-gray-400">Status</th>
                    <th className="pb-3 text-sm font-semibold text-gray-400 text-right">Avg Score</th>
                  </tr>
                </thead>
                <tbody>
                  {recentEvaluations.map((evalItem, idx) => (
                    <tr key={idx} className="border-b border-gray-50 hover:bg-brand-background/50 transition-colors">
                      <td className="py-4">
                        <div className="font-semibold text-brand-dark">{evalItem.subject}</div>
                        <div className="text-xs text-gray-400">{evalItem.id}</div>
                      </td>
                      <td className="py-4 text-sm text-gray-600">{evalItem.date}</td>
                      <td className="py-4 text-sm text-gray-600">{evalItem.students}</td>
                      <td className="py-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          evalItem.status === 'Completed' ? 'bg-brand-secondary text-brand-dark' : 'bg-yellow-50 text-yellow-600'
                        }`}>
                          {evalItem.status}
                        </span>
                      </td>
                      <td className="py-4 text-right font-semibold text-brand-primary">
                        {evalItem.score}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* 3. Right Column - Quick Actions & Reports */}
        <div className="space-y-8">
          
          {/* Quick Actions */}
          <div className="bg-white rounded-2xl p-6 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
            <h2 className="text-lg font-bold text-brand-dark mb-4">Quick Actions</h2>
            <div className="grid grid-cols-2 gap-4">
              <Link href="/upload" className="flex flex-col items-center justify-center p-4 bg-brand-background rounded-xl border border-gray-100 hover:border-brand-primary hover:bg-brand-secondary/30 transition-all group">
                <div className="w-10 h-10 rounded-full bg-brand-surface text-brand-primary flex items-center justify-center mb-2 group-hover:scale-110 transition-transform">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                </div>
                <span className="text-sm font-semibold text-brand-dark">Upload</span>
              </Link>
              
              <button className="flex flex-col items-center justify-center p-4 bg-brand-background rounded-xl border border-gray-100 hover:border-brand-primary hover:bg-brand-secondary/30 transition-all group">
                <div className="w-10 h-10 rounded-full bg-brand-surface text-brand-primary flex items-center justify-center mb-2 group-hover:scale-110 transition-transform">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
                </div>
                <span className="text-sm font-semibold text-brand-dark">New Class</span>
              </button>

              <button className="flex flex-col items-center justify-center p-4 bg-brand-background rounded-xl border border-gray-100 hover:border-brand-primary hover:bg-brand-secondary/30 transition-all group col-span-2">
                <div className="w-10 h-10 rounded-full bg-brand-primary text-white flex items-center justify-center mb-2 group-hover:scale-110 transition-transform shadow-md">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                </div>
                <span className="text-sm font-semibold text-brand-dark">Generate Custom Report</span>
              </button>
            </div>
          </div>

          {/* Recent Reports */}
          <div className="bg-white rounded-2xl p-6 shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
            <h2 className="text-lg font-bold text-brand-dark mb-4">Recent Reports</h2>
            <div className="space-y-4">
              {[
                { title: 'Math 101 Performance', date: '2 hours ago', type: 'PDF' },
                { title: 'Physics Midterm Insights', date: 'Yesterday', type: 'CSV' },
                { title: 'Student Risk Analysis', date: 'Oct 10', type: 'PDF' },
              ].map((report, idx) => (
                <div key={idx} className="flex items-center gap-4 p-3 rounded-xl hover:bg-brand-background transition-colors cursor-pointer border border-transparent hover:border-gray-100">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-xs ${report.type === 'PDF' ? 'bg-red-50 text-red-500' : 'bg-green-50 text-green-600'}`}>
                    {report.type}
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-brand-dark">{report.title}</h4>
                    <p className="text-xs text-gray-500">{report.date}</p>
                  </div>
                  <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </div>
              ))}
            </div>
            <button className="w-full mt-4 py-2 text-sm font-semibold text-brand-primary hover:text-brand-dark transition-colors border-t border-gray-50 pt-4">
              View All Reports
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
