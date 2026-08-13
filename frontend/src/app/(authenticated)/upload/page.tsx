'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { Check, Info, FileText as FileTextIcon } from 'lucide-react';
import { ExamService } from '@/services/exam.service';
import { SubmissionService } from '@/services/submission.service';

type FileType = 'questionPaper' | 'answerKey' | 'studentSheets';

interface StudentSheetItem {
  file: File;
  studentName: string;
  studentRollNumber: string;
}

const isPreviewableImage = (file: File) => file.type.startsWith('image/');

/**
 * Object-URL preview for a single file. Images get a real thumbnail; PDFs
 * (and anything else) get a document icon instead, since <embed> previews
 * for PDFs are heavy and inconsistent across browsers in a small thumbnail.
 * Revokes its object URL on unmount / file change to avoid leaking memory.
 */
function FilePreviewThumb({ file, size = 48 }: { file: File; size?: number }) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!isPreviewableImage(file)) {
      setUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  if (url) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={url}
        alt={`Preview of ${file.name}`}
        style={{ width: size, height: size }}
        className="rounded-lg object-cover border border-gray-200 shrink-0 bg-white"
      />
    );
  }

  return (
    <div
      style={{ width: size, height: size }}
      className="rounded-lg border border-gray-200 bg-brand-background flex items-center justify-center shrink-0"
      title={file.name}
    >
      <FileTextIcon className="w-5 h-5 text-brand-primary" aria-hidden="true" />
    </div>
  );
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

  // Load existing exams on mount
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
    { id: 1, title: 'Exam Configuration', key: 'questionPaper' as FileType, desc: 'Select or create the exam and upload the question paper' },
    { id: 2, title: 'Answer Key / Rubric', key: 'answerKey' as FileType, desc: 'Upload an optional answer key or rubric' },
    { id: 3, title: 'Student Sheets', key: 'studentSheets' as FileType, desc: 'Upload scanned student sheets and review metadata' },
  ];

  const currentStepData = steps[currentStep - 1];

  const parseFileName = (filename: string) => {
    const base = filename.replace(/\.[^/.]+$/, "");
    const rollMatch = base.match(/\d+/);
    const roll = rollMatch ? rollMatch[0] : "";
    const nameClean = base.replace(/\d+/g, "").replace(/[_-]/g, " ").trim();
    return {
      studentName: nameClean,
      studentRollNumber: roll
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
          setFiles(prev => ({
            ...prev,
            [currentStepData.key]: [...prev[currentStepData.key], ...droppedFiles]
          }));
        }
      }
    }
  }, [currentStep, currentStepData.key]);

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
        setFiles(prev => ({
          ...prev,
          [currentStepData.key]: [...prev[currentStepData.key], ...selectedFiles]
        }));
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

      // 1. Create a new exam if requested
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

      if (!examId) {
        throw new Error('Please select or create an exam.');
      }

      const selectedExam = exams.find(exam => exam.id === examId);
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
        throw new Error('Please enter student name and roll number for every answer sheet.');
      }

      // 2. Upload student sheets in parallel
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

      // 3. Redirect to evaluation screen with submission IDs
      router.push(`/evaluation?ids=${submissionIds.join(',')}`);
    } catch (err: any) {
      console.error('Submission pipeline failed:', err);
      setSubmitError(err.message || 'An error occurred during evaluation setup.');
      setIsSubmitting(false);
    }
  };

  const selectedExam = exams.find(exam => exam.id === selectedExamId);
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
    <div className="flex flex-col min-h-full">
      <header className="h-20 bg-white/50 backdrop-blur-md border-b border-gray-100/50 flex items-center px-8 sticky top-0 z-10">
        <h1 className="text-2xl font-bold text-brand-dark">New Evaluation Setup</h1>
      </header>

      <div className="flex-1 p-4 lg:p-6 w-full max-w-screen-2xl mx-auto flex flex-col gap-6">
          {/* Progress Tracker */}
          <div className="mb-10 bg-white p-6 rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex items-center justify-between relative">
            <div className="absolute top-1/2 left-10 right-10 h-1 bg-gray-100 -z-10 -translate-y-1/2 rounded-full">
               <div 
                 className="h-full bg-brand-primary transition-all duration-500 rounded-full" 
                 style={{ width: `${((currentStep - 1) / 2) * 100}%` }}
               />
            </div>
            
            {steps.map(step => (
              <div key={step.id} className="flex flex-col items-center gap-2 bg-white px-4">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold border-2 transition-colors ${
                  step.id < currentStep ? 'bg-brand-primary border-brand-primary text-white' :
                  step.id === currentStep ? 'bg-brand-surface border-brand-primary text-brand-dark' :
                  'bg-white border-gray-200 text-gray-400'
                }`}>
                  {step.id < currentStep ? <Check className="h-5 w-5" aria-hidden="true" /> : step.id}
                </div>
                <span className={`text-sm font-semibold ${step.id <= currentStep ? 'text-brand-dark' : 'text-gray-400'}`}>
                  {step.title}
                </span>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 flex-1">
            
            {/* Left Column: Configuration Forms / Illustration */}
            <div className="bg-white p-8 rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50 flex flex-col justify-between min-h-[400px]">
              
              {currentStep === 1 && (
                <div className="space-y-6">
                  <h3 className="text-xl font-bold text-brand-dark">Exam Selection</h3>
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-gray-500">Choose Exam</label>
                    <select 
                      value={selectedExamId}
                      onChange={(e) => setSelectedExamId(e.target.value)}
                      className="w-full p-3.5 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:border-brand-primary text-brand-dark font-medium"
                    >
                      {exams.map(exam => (
                        <option key={exam.id} value={exam.id}>{exam.title} ({exam.subject})</option>
                      ))}
                      <option value="new">+ Create New Exam</option>
                    </select>
                  </div>

                  {selectedExamId === 'new' && (
                    <div className="space-y-4 p-5 bg-brand-background rounded-xl border border-brand-primary/10">
                      <h4 className="font-bold text-brand-dark">New Exam details</h4>
                      <div className="space-y-2">
                        <label className="text-xs font-semibold text-gray-500">Exam Title</label>
                        <input 
                          type="text"
                          value={newExamTitle}
                          onChange={(e) => setNewExamTitle(e.target.value)}
                          placeholder="Midterm Exam"
                          className="w-full p-3 bg-white border border-gray-200 rounded-lg outline-none focus:border-brand-primary text-brand-dark text-sm font-medium"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-semibold text-gray-500">Subject</label>
                        <input 
                          type="text"
                          value={newExamSubject}
                          onChange={(e) => setNewExamSubject(e.target.value)}
                          placeholder="Physics"
                          className="w-full p-3 bg-white border border-gray-200 rounded-lg outline-none focus:border-brand-primary text-brand-dark text-sm font-medium"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-xs font-semibold text-gray-500">Total Marks</label>
                        <input 
                          type="number"
                          value={newExamTotalMarks}
                          onChange={(e) => setNewExamTotalMarks(parseInt(e.target.value) || 100)}
                          className="w-full p-3 bg-white border border-gray-200 rounded-lg outline-none focus:border-brand-primary text-brand-dark text-sm font-medium"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {currentStep === 2 && (
                <div className="space-y-4">
                  <h3 className="text-xl font-bold text-brand-dark">Answer Key / Rubric Setup</h3>
                  <p className="text-sm text-gray-500">
                    Answer keys are optional. Upload a rubric or answer key for answer-key scoring, or skip this step for autonomous AI evaluation.
                  </p>
                  <div className="p-4 bg-brand-secondary/30 border border-brand-primary/20 rounded-xl text-sm font-medium text-brand-dark flex items-start gap-3">
                    <Info className="mt-0.5 h-5 w-5 shrink-0 text-brand-primary" aria-hidden="true" />
                    <span>If no answer key is uploaded, GradeMIND will use autonomous AI evaluation with the uploaded question paper.</span>
                  </div>
                </div>
              )}

              {currentStep === 3 && (
                <div className="space-y-4">
                  <h3 className="text-xl font-bold text-brand-dark">Student Sheet Ingestion</h3>
                  <p className="text-sm text-gray-500">
                    Drag student sheets to the upload zone on the right. You can rename the students and adjust their roll numbers before evaluation.
                  </p>
                  {submitError && (
                    <div className="p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl text-sm font-semibold">
                      {submitError}
                    </div>
                  )}
                </div>
              )}

              {/* Step Illustration */}
              <div className="relative overflow-hidden rounded-xl border border-gray-100 flex-1 mt-6 min-h-[160px]">
                <Image 
                  src="/images/upload-illustration.png" 
                  alt="Upload Illustration" 
                  fill
                  className="object-cover object-center opacity-60 scale-105"
                  priority
                />
              </div>
            </div>

            {/* Right Column: Upload Zone / Student List */}
            <div className="flex flex-col h-full bg-white p-8 rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
              
              {/* Dropzone */}
              <div 
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={`flex-1 bg-gray-50 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center p-8 transition-all duration-200 min-h-[220px] ${
                  isDragging ? 'border-brand-primary bg-brand-surface/30' : 'border-gray-200 hover:border-brand-primary/50'
                }`}
              >
                <div className="w-12 h-12 bg-brand-secondary rounded-full flex items-center justify-center text-brand-primary mb-3">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                </div>
                <h3 className="text-base font-bold text-brand-dark mb-1">Drag & Drop files here</h3>
                <p className="text-xs text-gray-400 mb-4">or</p>
                <label className="bg-brand-primary text-white px-5 py-2 rounded-xl text-sm font-semibold cursor-pointer hover:bg-opacity-90 transition-all shadow-sm">
                  Browse Files
                  <input type="file" multiple className="hidden" onChange={handleFileInput} />
                </label>
                <p className="text-[10px] text-gray-400 mt-4">PDF, JPG, PNG up to 50MB</p>
              </div>

              {/* Student Metadata Form (Only Step 3) */}
              {currentStep === 3 && studentSheetsList.length > 0 && (
                <div className="mt-6 space-y-4 max-h-[300px] overflow-y-auto pr-2">
                  <h4 className="text-sm font-bold text-brand-dark">Review Student Metadata ({studentSheetsList.length})</h4>
                  <div className="space-y-3">
                    {studentSheetsList.map((item, idx) => (
                      <div key={idx} className="p-4 bg-brand-background rounded-xl border border-gray-100 space-y-3 relative">
                        <button 
                          onClick={() => removeFile('studentSheets', idx)} 
                          className="absolute top-2 right-2 text-gray-400 hover:text-red-500 p-1"
                        >
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                        <div className="flex items-center gap-3">
                          <FilePreviewThumb file={item.file} size={40} />
                          <div className="text-xs font-medium text-gray-400 truncate max-w-[75%]">File: {item.file.name}</div>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="text-[10px] font-semibold text-gray-500">Student Name</label>
                            <input 
                              type="text" 
                              value={item.studentName}
                              onChange={(e) => updateStudentMetadata(idx, 'studentName', e.target.value)}
                              className="w-full p-2 bg-white border border-gray-200 rounded-lg outline-none text-xs text-brand-dark font-medium"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] font-semibold text-gray-500">Roll Number</label>
                            <input 
                              type="text" 
                              value={item.studentRollNumber}
                              onChange={(e) => updateStudentMetadata(idx, 'studentRollNumber', e.target.value)}
                              className="w-full p-2 bg-white border border-gray-200 rounded-lg outline-none text-xs text-brand-dark font-medium"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Standard previews (Step 1 & 2) */}
              {currentStep < 3 && files[currentStepData.key].length > 0 && (
                <div className="mt-6 p-4 bg-brand-background rounded-xl border border-gray-100 max-h-48 overflow-y-auto space-y-2">
                  <div className="text-xs font-bold text-brand-dark mb-2">Uploaded Document</div>
                  {files[currentStepData.key].map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between gap-3 py-1 text-xs font-semibold text-brand-dark">
                      <div className="flex items-center gap-3 min-w-0">
                        <FilePreviewThumb file={file} size={40} />
                        <span className="truncate">{file.name}</span>
                      </div>
                      <button onClick={() => removeFile(currentStepData.key, idx)} className="text-red-500 hover:text-red-700 shrink-0">Delete</button>
                    </div>
                  ))}
                </div>
              )}

            </div>
          </div>

          {/* Action Buttons */}
          <div className="mt-8 flex justify-between items-center bg-white p-6 rounded-2xl shadow-[0_4px_20px_rgba(47,90,58,0.05)] border border-gray-50">
            <button 
              onClick={() => setCurrentStep(prev => Math.max(1, prev - 1))}
              disabled={currentStep === 1 || isSubmitting}
              className="px-6 py-3 rounded-xl font-medium text-brand-dark bg-gray-50 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Back
            </button>
            
            {currentStep < 3 ? (
              <button 
                onClick={() => setCurrentStep(prev => Math.min(3, prev + 1))}
                disabled={!canProceed}
                className="px-8 py-3 rounded-xl font-medium text-white bg-brand-primary hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all shadow-md"
              >
                Continue to Next Step
              </button>
            ) : (
              <button 
                onClick={handleStartEvaluation}
                disabled={!canProceed || isSubmitting}
                className="px-10 py-4 rounded-xl font-bold text-white bg-brand-accent hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95 transition-all shadow-[0_10px_30px_rgba(91,141,239,0.3)] flex items-center gap-2 text-lg"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Starting Evaluation...
                  </>
                ) : (
                  <>
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    Start AI Evaluation
                  </>
                )}
              </button>
            )}
          </div>

      </div>
    </div>
  );
}

