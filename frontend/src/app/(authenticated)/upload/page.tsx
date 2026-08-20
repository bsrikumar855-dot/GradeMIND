'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Check, 
  UploadCloud, 
  FileText, 
  Trash2, 
  Plus, 
  ArrowRight, 
  ArrowLeft, 
  Sparkles, 
  User, 
  Hash, 
  HelpCircle,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { ExamService } from '@/services/exam.service';
import { SubmissionService } from '@/services/submission.service';

type FileType = 'questionPaper' | 'answerKey' | 'studentSheets';

interface StudentSheetItem {
  file: File;
  studentName: string;
  studentRollNumber: string;
}

export default function UploadCenter() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [exams, setExams] = useState<any[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>('');
  
  // New Exam fields
  const [newExamTitle, setNewExamTitle] = useState('');
  const [newExamSubject, setNewExamSubject] = useState('');
  const [newExamTotalMarks, setNewExamTotalMarks] = useState(100);

  // Files state
  const [files, setFiles] = useState<Record<FileType, File[]>>({
    questionPaper: [],
    answerKey: [],
    studentSheets: [],
  });

  const [studentSheetsList, setStudentSheetsList] = useState<StudentSheetItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    async function loadExams() {
      try {
        const res = await ExamService.getExams();
        if (res.success && Array.isArray(res.data)) {
          setExams(res.data);
          if (res.data.length > 0) {
            setSelectedExamId(res.data[0].id);
          } else {
            setSelectedExamId('new');
          }
        } else {
          setSelectedExamId('new');
        }
      } catch (err) {
        console.error('Failed to load exams:', err);
        setSelectedExamId('new');
      }
    }
    loadExams();
  }, []);

  const steps = [
    { id: 1, title: 'Exam Details & QP', desc: 'Select/Create exam & upload question paper' },
    { id: 2, title: 'Marking Scheme', desc: 'Upload optional answer key or use AI Autonomous' },
    { id: 3, title: 'Student Sheets', desc: 'Upload answer sheets and verify student metadata' },
  ];

  const parseFileName = (filename: string) => {
    const base = filename.replace(/\.[^/.]+$/, "");
    const rollMatch = base.match(/\d+/);
    const roll = rollMatch ? rollMatch[0] : "";
    const nameClean = base.replace(/\d+/g, "").replace(/[_-]/g, " ").trim();
    return {
      studentName: nameClean || "Student",
      studentRollNumber: roll || "REG101"
    };
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      if (droppedFiles.length > 0) {
        if (currentStep === 3) {
          const newList = droppedFiles.map(file => {
            const { studentName, studentRollNumber } = parseFileName(file.name);
            return { file, studentName, studentRollNumber };
          });
          setStudentSheetsList(prev => [...prev, ...newList]);
        } else {
          const key: FileType = currentStep === 1 ? 'questionPaper' : 'answerKey';
          setFiles(prev => ({ ...prev, [key]: [...prev[key], ...droppedFiles] }));
        }
      }
    }
  }, [currentStep]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      if (currentStep === 3) {
        const newList = selectedFiles.map(file => {
          const { studentName, studentRollNumber } = parseFileName(file.name);
          return { file, studentName, studentRollNumber };
        });
        setStudentSheetsList(prev => [...prev, ...newList]);
      } else {
        const key: FileType = currentStep === 1 ? 'questionPaper' : 'answerKey';
        setFiles(prev => ({ ...prev, [key]: [...prev[key], ...selectedFiles] }));
      }
    }
  };

  const removeFile = (fileType: FileType, index: number) => {
    if (fileType === 'studentSheets') {
      setStudentSheetsList(prev => prev.filter((_, i) => i !== index));
    } else {
      setFiles(prev => ({
        ...prev,
        [fileType]: prev[fileType].filter((_, i) => i !== index)
      }));
    }
  };

  const updateStudentMetadata = (index: number, field: 'studentName' | 'studentRollNumber', value: string) => {
    setStudentSheetsList(prev => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const handleStartEvaluation = async () => {
    setSubmitError('');
    setIsSubmitting(true);
    try {
      let examId = selectedExamId;

      if (selectedExamId === 'new') {
        if (!newExamTitle.trim() || !newExamSubject.trim()) {
          throw new Error('Please enter Exam Title and Subject.');
        }
        const newExamRes = await ExamService.createExam({
          title: newExamTitle,
          subject: newExamSubject,
          total_marks: newExamTotalMarks,
          question_paper_url: null,
          answer_key_url: null,
          evaluation_mode: files.answerKey.length > 0 ? 'ANSWER_KEY' : 'AI_AUTONOMOUS'
        });
        if (newExamRes.id) {
          examId = newExamRes.id;
        } else {
          throw new Error('Failed to create the exam on the backend.');
        }
      }

      if (!examId) throw new Error('Please select or create an exam.');

      const selectedExam = exams.find(e => e.id === examId);
      const hasQuestionPaper = files.questionPaper.length > 0 || Boolean(selectedExam?.question_paper_url);
      if (!hasQuestionPaper) {
        throw new Error('Please upload the question paper in Step 1 before starting evaluation.');
      }

      if (files.questionPaper.length > 0) {
        await ExamService.uploadQuestionPaper(examId, files.questionPaper[0]);
      }

      if (files.answerKey.length > 0) {
        await ExamService.uploadAnswerKey(examId, files.answerKey[0]);
      }

      if (studentSheetsList.length === 0) {
        throw new Error('Please upload at least one student answer sheet.');
      }

      const missingMetadata = studentSheetsList.find(
        (item) => !item.studentName.trim() || !item.studentRollNumber.trim()
      );
      if (missingMetadata) {
        throw new Error('Please fill in Student Name and Roll Number for all answer sheets.');
      }

      const uploadPromises = studentSheetsList.map(item => 
        SubmissionService.upload({
          exam_id: examId,
          student_name: item.studentName,
          student_roll_number: item.studentRollNumber,
          file: item.file
        })
      );

      const uploadResults = await Promise.all(uploadPromises);
      const submissionIds = uploadResults.map(res => res.id || res.data?.id).filter(Boolean);

      if (submissionIds.length === 0) {
        throw new Error('No submissions were successfully registered.');
      }

      router.push(`/evaluation?ids=${submissionIds.join(',')}`);
    } catch (err: any) {
      console.error('Submission pipeline failed:', err);
      setSubmitError(err.message || 'An error occurred during evaluation setup.');
      setIsSubmitting(false);
    }
  };

  const selectedExam = exams.find(e => e.id === selectedExamId);
  const isStep1Valid = (selectedExamId !== 'new' || (newExamTitle.trim() !== '' && newExamSubject.trim() !== '')) && (files.questionPaper.length > 0 || Boolean(selectedExam?.question_paper_url));
  const isStep2Valid = true;
  const isStep3Valid = studentSheetsList.length > 0 && studentSheetsList.every(
    (item) => item.studentName.trim() && item.studentRollNumber.trim()
  );

  const canProceed = 
    currentStep === 1 ? isStep1Valid :
    currentStep === 2 ? isStep2Valid :
    isStep3Valid;

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16">
      
      {/* Header Banner */}
      <div className="calm-card p-6">
        <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold uppercase tracking-wider mb-2">
          Assessment Intake Workflow
        </div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Upload & Configure Evaluation
        </h1>
        <p className="text-slate-600 text-sm mt-1">
          Follow the 3-step setup to upload, process, and evaluate student answer scripts.
        </p>
      </div>

      {/* 21st.dev Style Step Tracker */}
      <div className="glass-card rounded-3xl p-6 relative">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative z-10">
          {steps.map((step) => {
            const isCompleted = currentStep > step.id;
            const isCurrent = currentStep === step.id;
            return (
              <div 
                key={step.id} 
                onClick={() => isCompleted && setCurrentStep(step.id)}
                className={`p-4 rounded-2xl border transition-all duration-300 ${
                  isCurrent 
                    ? 'bg-slate-900 text-white border-slate-900 shadow-xl shadow-slate-900/10' 
                    : isCompleted 
                    ? 'bg-emerald-50 text-slate-900 border-emerald-200 cursor-pointer hover:bg-emerald-100/60' 
                    : 'bg-slate-50/50 text-slate-400 border-slate-200/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-bold text-xs ${
                    isCurrent ? 'bg-emerald-500 text-slate-950' : isCompleted ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'
                  }`}>
                    {isCompleted ? <Check className="w-4 h-4" /> : step.id}
                  </div>
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider">{step.title}</h3>
                    <p className={`text-[11px] mt-0.5 ${isCurrent ? 'text-slate-300' : 'text-slate-500'}`}>{step.desc}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Step Content Card */}
      <div className="glass-card rounded-3xl p-8 space-y-6">
        
        {/* STEP 1: EXAM SELECTION & QUESTION PAPER */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Step 1: Exam Configuration & Question Paper</h2>
              <p className="text-xs text-slate-500 mt-1">Select an existing exam package or create a new exam title.</p>
            </div>

            {/* Exam Select */}
            <div className="space-y-4">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">Target Exam Package</label>
              <select
                value={selectedExamId}
                onChange={(e) => setSelectedExamId(e.target.value)}
                className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-slate-900 text-sm font-medium focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
              >
                <option value="new">+ Create New Exam Package</option>
                {exams.map(e => (
                  <option key={e.id} value={e.id}>{e.title} ({e.subject}) — {e.total_marks} Marks</option>
                ))}
              </select>
            </div>

            {/* New Exam Form */}
            {selectedExamId === 'new' && (
              <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Exam Title *</label>
                  <input
                    type="text"
                    placeholder="e.g. Data Structures Mid-Sem 2026"
                    value={newExamTitle}
                    onChange={(e) => setNewExamTitle(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-900 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Subject *</label>
                  <input
                    type="text"
                    placeholder="e.g. Data Structures & Algorithms"
                    value={newExamSubject}
                    onChange={(e) => setNewExamSubject(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-900 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Total Marks *</label>
                  <input
                    type="number"
                    value={newExamTotalMarks}
                    onChange={(e) => setNewExamTotalMarks(Number(e.target.value))}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-900 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>
            )}

            {/* Question Paper Drag & Drop */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">Question Paper File (Image or PDF) *</label>
              
              <div 
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-3xl p-8 text-center transition-all duration-300 ${
                  isDragging ? 'border-emerald-500 bg-emerald-50/50 scale-[0.99]' : 'border-slate-300 hover:border-emerald-500/50 bg-slate-50/50'
                }`}
              >
                <UploadCloud className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                <h4 className="text-sm font-bold text-slate-900">Drag & Drop Question Paper Here</h4>
                <p className="text-xs text-slate-400 mt-1">Supports JPEG, PNG, or PDF format</p>
                
                <label className="mt-4 inline-block px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl cursor-pointer transition-all">
                  Browse File
                  <input type="file" onChange={handleFileInput} accept="image/*,.pdf" className="hidden" />
                </label>
              </div>

              {/* Uploaded Question Paper List */}
              {files.questionPaper.length > 0 && (
                <div className="mt-4 space-y-2">
                  {files.questionPaper.map((f, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-slate-900 text-xs font-semibold">
                      <div className="flex items-center gap-3">
                        <FileText className="w-4 h-4 text-emerald-600" />
                        <span>{f.name} ({(f.size / 1024).toFixed(1)} KB)</span>
                      </div>
                      <button onClick={() => removeFile('questionPaper', idx)} className="text-rose-500 hover:text-rose-700 p-1">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* STEP 2: ANSWER KEY / RUBRIC */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Step 2: Marking Scheme / Answer Key (Optional)</h2>
              <p className="text-xs text-slate-500 mt-1">
                Upload a official answer key if available. If skipped, GradeMIND automatically runs in 
                <span className="font-bold text-emerald-600"> AI Autonomous Evaluation Mode</span>.
              </p>
            </div>

            <div 
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-3xl p-8 text-center transition-all duration-300 ${
                isDragging ? 'border-emerald-500 bg-emerald-50/50 scale-[0.99]' : 'border-slate-300 hover:border-emerald-500/50 bg-slate-50/50'
              }`}
            >
              <UploadCloud className="w-12 h-12 text-blue-500 mx-auto mb-3" />
              <h4 className="text-sm font-bold text-slate-900">Drag & Drop Answer Key / Solution Paper</h4>
              <p className="text-xs text-slate-400 mt-1">Optional. Leave empty to use Autonomous AI Grading</p>
              
              <label className="mt-4 inline-block px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl cursor-pointer transition-all">
                Select File
                <input type="file" onChange={handleFileInput} accept="image/*,.pdf" className="hidden" />
              </label>
            </div>

            {files.answerKey.length > 0 && (
              <div className="space-y-2">
                {files.answerKey.map((f, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-slate-900 text-xs font-semibold">
                    <div className="flex items-center gap-3">
                      <FileText className="w-4 h-4 text-blue-600" />
                      <span>{f.name} ({(f.size / 1024).toFixed(1)} KB)</span>
                    </div>
                    <button onClick={() => removeFile('answerKey', idx)} className="text-rose-500 hover:text-rose-700 p-1">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* STEP 3: STUDENT SHEETS & METADATA */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Step 3: Student Answer Sheets & Roll Numbers</h2>
              <p className="text-xs text-slate-500 mt-1">Upload student answer sheet scans and verify candidate metadata.</p>
            </div>

            <div 
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-3xl p-8 text-center transition-all duration-300 ${
                isDragging ? 'border-emerald-500 bg-emerald-50/50 scale-[0.99]' : 'border-slate-300 hover:border-emerald-500/50 bg-slate-50/50'
              }`}
            >
              <UploadCloud className="w-12 h-12 text-purple-500 mx-auto mb-3" />
              <h4 className="text-sm font-bold text-slate-900">Drag & Drop Student Answer Sheets</h4>
              <p className="text-xs text-slate-400 mt-1">Batch upload JPEG, PNG, or scanned PDFs</p>
              
              <label className="mt-4 inline-block px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl cursor-pointer transition-all">
                Select Student Sheets
                <input type="file" multiple onChange={handleFileInput} accept="image/*,.pdf" className="hidden" />
              </label>
            </div>

            {/* Student Sheets Metadata Editor List */}
            {studentSheetsList.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Candidate Sheet List ({studentSheetsList.length})</h4>
                <div className="divide-y divide-slate-100 rounded-2xl bg-slate-50 border border-slate-200/80 overflow-hidden">
                  {studentSheetsList.map((item, idx) => (
                    <div key={idx} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-white transition-colors">
                      <div className="flex items-center gap-3 min-w-[200px]">
                        <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center font-bold text-xs">
                          #{idx + 1}
                        </div>
                        <div className="truncate">
                          <span className="block text-xs font-bold text-slate-900 truncate">{item.file.name}</span>
                          <span className="text-[10px] text-slate-400">{(item.file.size / 1024).toFixed(1)} KB</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 flex-1">
                        <div className="flex-1 relative">
                          <User className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                          <input
                            type="text"
                            placeholder="Student Name *"
                            value={item.studentName}
                            onChange={(e) => updateStudentMetadata(idx, 'studentName', e.target.value)}
                            className="w-full pl-8 pr-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:border-emerald-500"
                          />
                        </div>
                        <div className="flex-1 relative">
                          <Hash className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                          <input
                            type="text"
                            placeholder="Roll Number *"
                            value={item.studentRollNumber}
                            onChange={(e) => updateStudentMetadata(idx, 'studentRollNumber', e.target.value)}
                            className="w-full pl-8 pr-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:border-emerald-500"
                          />
                        </div>
                        <button 
                          onClick={() => removeFile('studentSheets', idx)}
                          className="p-2 text-rose-500 hover:bg-rose-50 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Error message banner */}
        {submitError && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-xs font-bold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{submitError}</span>
          </div>
        )}

        {/* Navigation Footer Controls */}
        <div className="flex justify-between items-center pt-4 border-t border-slate-100">
          {currentStep > 1 ? (
            <button
              onClick={() => setCurrentStep(prev => prev - 1)}
              className="px-5 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs rounded-xl transition-all flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" /> Previous Step
            </button>
          ) : <div />}

          {currentStep < 3 ? (
            <button
              onClick={() => canProceed && setCurrentStep(prev => prev + 1)}
              disabled={!canProceed}
              className={`px-6 py-2.5 font-bold text-xs rounded-xl transition-all flex items-center gap-2 ${
                canProceed ? 'bg-slate-900 hover:bg-slate-800 text-white shadow-lg shadow-slate-900/20' : 'bg-slate-200 text-slate-400 cursor-not-allowed'
              }`}
            >
              Next Step <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleStartEvaluation}
              disabled={isSubmitting || !canProceed}
              className={`px-8 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-black text-sm rounded-xl transition-all shadow-xl shadow-emerald-500/25 flex items-center gap-2 ${
                (isSubmitting || !canProceed) ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Initiating AI Pipeline...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" /> Start AI Evaluation
                </>
              )}
            </button>
          )}
        </div>

      </div>

    </div>
  );
}
