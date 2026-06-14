'use client';

import React, { useState } from 'react';
import { Search, Filter, Download, Eye, FileText, X, CheckCircle2, ChevronDown } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

const MOCK_REPORTS = [
  { id: 'REP-001', student: 'Alex Johnson', subject: 'Advanced Physics', marks: '86', max: '100', date: '2026-06-12', grade: 'A' },
  { id: 'REP-002', student: 'Maria Garcia', subject: 'Linear Algebra', marks: '92', max: '100', date: '2026-06-11', grade: 'A+' },
  { id: 'REP-003', student: 'James Smith', subject: 'Advanced Physics', marks: '74', max: '100', date: '2026-06-11', grade: 'C' },
  { id: 'REP-004', student: 'Sarah Lee', subject: 'Organic Chemistry', marks: '88', max: '100', date: '2026-06-10', grade: 'B+' },
  { id: 'REP-005', student: 'Michael Chen', subject: 'Linear Algebra', marks: '65', max: '100', date: '2026-06-09', grade: 'D' },
  { id: 'REP-006', student: 'Emily Davis', subject: 'Organic Chemistry', marks: '95', max: '100', date: '2026-06-08', grade: 'A+' },
  { id: 'REP-007', student: 'David Wilson', subject: 'Advanced Physics', marks: '82', max: '100', date: '2026-06-08', grade: 'B' },
];

export default function ReportsCenter() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('All');
  const [previewReport, setPreviewReport] = useState<typeof MOCK_REPORTS[0] | null>(null);

  // Derive unique subjects for filter
  const subjects = ['All', ...Array.from(new Set(MOCK_REPORTS.map(r => r.subject)))];

  // Filter reports
  const filteredReports = MOCK_REPORTS.filter(report => {
    const matchesSearch = report.student.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          report.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSubject = selectedSubject === 'All' || report.subject === selectedSubject;
    return matchesSearch && matchesSubject;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h1 className="text-3xl font-bold text-brand-dark flex items-center gap-3">
            <div className="p-2 bg-brand-primary/10 rounded-xl">
              <FileText className="w-6 h-6 text-brand-primary" />
            </div>
            Reports Center
          </h1>
          <p className="text-gray-500 mt-2 font-medium">Manage and export AI-generated evaluation reports.</p>
        </div>
        
        <div className="flex gap-4 w-full md:w-auto">
          {/* Search */}
          <div className="relative flex-1 md:w-72">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input 
              type="text" 
              placeholder="Search student or ID..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-11 pr-4 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all shadow-sm"
            />
          </div>
          
          {/* Filter */}
          <div className="relative">
            <select 
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="appearance-none pl-11 pr-10 py-3 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary transition-all shadow-sm text-brand-dark font-medium min-w-[160px] cursor-pointer"
            >
              {subjects.map(sub => <option key={sub} value={sub}>{sub}</option>)}
            </select>
            <Filter className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Reports Table */}
      <div className="bg-white rounded-[24px] shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-brand-background/50 border-b border-gray-100">
                <th className="py-5 px-6 text-xs font-bold text-gray-500 uppercase tracking-wider">Report ID</th>
                <th className="py-5 px-6 text-xs font-bold text-gray-500 uppercase tracking-wider">Student</th>
                <th className="py-5 px-6 text-xs font-bold text-gray-500 uppercase tracking-wider">Subject</th>
                <th className="py-5 px-6 text-xs font-bold text-gray-500 uppercase tracking-wider">Marks</th>
                <th className="py-5 px-6 text-xs font-bold text-gray-500 uppercase tracking-wider">Date Evaluated</th>
                <th className="py-5 px-6 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filteredReports.map((report) => (
                <tr key={report.id} className="hover:bg-brand-background/30 transition-colors group">
                  <td className="py-4 px-6">
                    <span className="font-mono text-xs font-bold text-gray-400 bg-gray-50 px-2 py-1 rounded-md border border-gray-100">
                      {report.id}
                    </span>
                  </td>
                  <td className="py-4 px-6 font-bold text-brand-dark">{report.student}</td>
                  <td className="py-4 px-6">
                    <span className="text-sm font-semibold text-gray-600 bg-[#EEF7E8] px-3 py-1 rounded-full border border-brand-primary/20">
                      {report.subject}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <span className="font-extrabold text-brand-dark">{report.marks}</span>
                      <span className="text-xs text-gray-400 font-medium">/ {report.max}</span>
                      <span className={`ml-2 text-xs font-bold px-2 py-0.5 rounded ${
                        report.grade.includes('A') ? 'bg-green-100 text-green-700' :
                        report.grade.includes('B') ? 'bg-blue-100 text-blue-700' :
                        report.grade.includes('C') ? 'bg-yellow-100 text-yellow-700' :
                        'bg-red-100 text-red-700'
                      }`}>
                        {report.grade}
                      </span>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-sm font-medium text-gray-500">{report.date}</td>
                  <td className="py-4 px-6">
                    <div className="flex items-center justify-end gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button 
                        onClick={() => setPreviewReport(report)}
                        className="p-2 text-brand-accent hover:bg-brand-accent/10 rounded-lg transition-colors"
                        title="Preview"
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                      <button 
                        className="p-2 text-brand-primary hover:bg-brand-primary/10 rounded-lg transition-colors"
                        title="Download PDF"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredReports.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-gray-500 font-medium">
                    No reports found matching your criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Preview Modal overlay using Framer Motion */}
      <AnimatePresence>
        {previewReport && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setPreviewReport(null)}
              className="absolute inset-0 bg-brand-dark/40 backdrop-blur-sm"
            />
            
            {/* Modal Content */}
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative w-full max-w-3xl bg-white rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
            >
              {/* Modal Header */}
              <div className="px-8 py-6 border-b border-gray-100 flex items-center justify-between bg-brand-background/30">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-brand-primary rounded-xl flex items-center justify-center">
                    <FileText className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-brand-dark">Report Preview</h2>
                    <p className="text-sm text-gray-500 font-mono mt-0.5">{previewReport.id}</p>
                  </div>
                </div>
                <button 
                  onClick={() => setPreviewReport(null)}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Modal Body (Mock PDF Layout) */}
              <div className="p-8 overflow-y-auto bg-gray-50/50 flex-1">
                <div className="bg-white p-10 shadow-sm border border-gray-200 rounded-xl max-w-2xl mx-auto space-y-8 relative">
                  {/* Watermark */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-[0.03]">
                    <span className="text-9xl font-extrabold uppercase -rotate-45">GradeMIND</span>
                  </div>

                  {/* PDF Header */}
                  <div className="flex justify-between items-start border-b-2 border-gray-900 pb-6 relative z-10">
                     <div>
                       <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">GradeMIND Evaluation</h1>
                       <p className="text-gray-500 mt-1 font-medium">Official AI Generated Assessment</p>
                     </div>
                     <div className="text-right">
                       <p className="text-sm font-bold text-gray-400 uppercase tracking-wider">Date</p>
                       <p className="font-semibold text-gray-900">{previewReport.date}</p>
                     </div>
                  </div>

                  {/* Student Details Grid */}
                  <div className="grid grid-cols-2 gap-6 relative z-10">
                    <div>
                      <p className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-1">Student Name</p>
                      <p className="text-xl font-bold text-gray-900">{previewReport.student}</p>
                    </div>
                    <div>
                      <p className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-1">Subject / Course</p>
                      <p className="text-xl font-bold text-gray-900">{previewReport.subject}</p>
                    </div>
                  </div>

                  {/* Big Score Box */}
                  <div className="bg-gray-50 p-6 rounded-2xl border border-gray-200 flex items-center justify-between relative z-10">
                    <div>
                      <p className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">Final Score</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-5xl font-extrabold text-gray-900">{previewReport.marks}</span>
                        <span className="text-xl font-bold text-gray-400">/ {previewReport.max}</span>
                      </div>
                    </div>
                    <div className="text-right">
                       <p className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">Grade Achieved</p>
                       <span className="text-4xl font-extrabold text-brand-primary">{previewReport.grade}</span>
                    </div>
                  </div>

                  {/* Authentication Footer */}
                  <div className="pt-8 border-t border-gray-100 flex items-center gap-3 relative z-10">
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                    <p className="text-sm text-gray-500 font-medium">Verified and evaluated by GradeMIND AI Pipeline Version 2.4.0</p>
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-8 py-5 border-t border-gray-100 bg-white flex justify-end gap-4">
                <button 
                  onClick={() => setPreviewReport(null)}
                  className="px-6 py-2.5 rounded-xl font-bold text-gray-600 hover:bg-gray-100 transition-colors"
                >
                  Close
                </button>
                <button className="px-6 py-2.5 rounded-xl font-bold text-white bg-brand-primary hover:bg-opacity-90 active:scale-95 transition-all shadow-md flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  Download Full PDF
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
