import React from 'react';
import { ExamDetails } from './types';
import { BookOpen, Calendar, FileText, Hash } from 'lucide-react';

interface ExamFormProps {
  details: ExamDetails;
  onChange: (details: ExamDetails) => void;
}

export function ExamForm({ details, onChange }: ExamFormProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    onChange({
      ...details,
      [name]: name === 'total_marks' ? (value === '' ? 0 : Number(value)) : value,
    });
  };

  return (
    <div className="w-full h-full flex-1 p-10 md:p-14 flex flex-col justify-center gap-10">
      <div className="mb-4">
        <h2 className="text-3xl font-bold text-brand-dark mb-3">Exam Details</h2>
        <p className="text-gray-500 text-lg">Provide the core metadata for this evaluation run.</p>
      </div>

      <div className="flex flex-col gap-8">
        <div className="space-y-3">
          <label className="text-base font-semibold text-brand-dark flex items-center gap-2.5">
            <FileText className="w-5 h-5 text-brand-primary" />
            Exam Title
          </label>
          <input
            type="text"
            name="title"
            value={details.title}
            onChange={handleChange}
            placeholder="e.g., Midterm Physics 101"
            className="w-full bg-gray-50 border border-gray-200 rounded-xl px-5 py-4 text-lg text-brand-dark focus:outline-none focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary transition-all placeholder:text-gray-400"
          />
        </div>

        <div className="space-y-3">
          <label className="text-base font-semibold text-brand-dark flex items-center gap-2.5">
            <BookOpen className="w-5 h-5 text-brand-primary" />
            Subject Area
          </label>
          <input
            type="text"
            name="subject"
            value={details.subject}
            onChange={handleChange}
            placeholder="e.g., Advanced Mechanics"
            className="w-full bg-gray-50 border border-gray-200 rounded-xl px-5 py-4 text-lg text-brand-dark focus:outline-none focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary transition-all placeholder:text-gray-400"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-3">
            <label className="text-base font-semibold text-brand-dark flex items-center gap-2.5">
              <Hash className="w-5 h-5 text-brand-primary" />
              Total Marks
            </label>
            <input
              type="number"
              name="total_marks"
              value={details.total_marks || ''}
              onChange={handleChange}
              min="0"
              placeholder="100"
              className="w-full bg-gray-50 border border-gray-200 rounded-xl px-5 py-4 text-lg text-brand-dark focus:outline-none focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary transition-all placeholder:text-gray-400"
            />
          </div>

          <div className="space-y-3">
            <label className="text-base font-semibold text-brand-dark flex items-center gap-2.5">
              <Calendar className="w-5 h-5 text-brand-primary" />
              Exam Date
            </label>
            <input
              type="date"
              name="exam_date"
              value={details.exam_date}
              onChange={handleChange}
              className="w-full bg-gray-50 border border-gray-200 rounded-xl px-5 py-4 text-lg text-brand-dark focus:outline-none focus:ring-2 focus:ring-brand-primary/50 focus:border-brand-primary transition-all"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
