import React, { useState, useCallback } from 'react';
import { UploadState } from './types';
import { FileUp, CheckCircle2, X } from 'lucide-react';
import { cn } from '@/utils/cn';

interface DropzoneContainerProps {
  files: UploadState['files'];
  onChange: (files: UploadState['files']) => void;
}

type DropzoneType = 'questionPaper' | 'answerKey';

export function DropzoneContainer({ files, onChange }: DropzoneContainerProps) {
  const [dragging, setDragging] = useState<Record<DropzoneType, boolean>>({
    questionPaper: false,
    answerKey: false,
  });

  const handleDragOver = useCallback((e: React.DragEvent, type: DropzoneType) => {
    e.preventDefault();
    setDragging(prev => ({ ...prev, [type]: true }));
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent, type: DropzoneType) => {
    e.preventDefault();
    setDragging(prev => ({ ...prev, [type]: false }));
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, type: DropzoneType) => {
    e.preventDefault();
    setDragging(prev => ({ ...prev, [type]: false }));
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      onChange({
        ...files,
        [type]: [...files[type], ...droppedFiles],
      });
    }
  }, [files, onChange]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>, type: DropzoneType) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFiles = Array.from(e.target.files);
      onChange({
        ...files,
        [type]: [...files[type], ...selectedFiles],
      });
    }
  };

  const removeFile = (type: DropzoneType, index: number) => {
    onChange({
      ...files,
      [type]: files[type].filter((_, i) => i !== index),
    });
  };

  const renderDropzone = (
    type: DropzoneType,
    title: string,
    desc: string,
    accept: string
  ) => {
    const isDragging = dragging[type];
    const hasFiles = files[type].length > 0;

    return (
      <div className="flex flex-col flex-1 bg-gray-50/30 rounded-2xl p-8 border border-gray-100">
        <div className="mb-5">
          <h3 className="text-2xl font-bold text-brand-dark flex items-center gap-3">
            {title}
            {hasFiles && <CheckCircle2 className="w-6 h-6 text-green-500" />}
          </h3>
          <p className="text-base text-gray-500 mt-1">{desc}</p>
        </div>

        <div
          onDragOver={(e) => handleDragOver(e, type)}
          onDragLeave={(e) => handleDragLeave(e, type)}
          onDrop={(e) => handleDrop(e, type)}
          className={cn(
            "flex-1 rounded-xl border-2 border-dashed flex flex-col items-center justify-center p-10 transition-all min-h-[220px]",
            isDragging ? "border-brand-primary bg-brand-surface/30" : "border-gray-200 hover:border-brand-primary/50 bg-gray-50/50"
          )}
        >
          <div className="w-16 h-16 bg-brand-secondary rounded-full flex items-center justify-center text-brand-primary mb-5">
            <FileUp className="w-7 h-7" />
          </div>
          <p className="font-semibold text-brand-dark text-lg mb-1">Drag & drop files here</p>
          <p className="text-base text-gray-500 mb-6">Supports {accept}</p>
          
          <label className="bg-white border border-gray-200 text-brand-dark hover:text-brand-primary px-6 py-3 rounded-lg font-medium cursor-pointer transition-colors shadow-sm text-base">
            Browse Files
            <input 
              type="file" 
              multiple 
              className="hidden" 
              accept={accept.toLowerCase().replace(' ', ', ')} 
              onChange={(e) => handleFileInput(e, type)} 
            />
          </label>
        </div>

        {hasFiles && (
          <div className="mt-5 space-y-2.5 max-h-[160px] overflow-y-auto pr-2 custom-scrollbar">
            {files[type].map((file, idx) => (
              <div key={idx} className="flex items-center justify-between p-3.5 bg-brand-secondary/30 rounded-lg border border-brand-primary/20">
                <div className="flex items-center gap-3 overflow-hidden">
                  <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                  <span className="text-base font-medium text-brand-dark truncate">{file.name}</span>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="text-sm text-brand-primary font-medium">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                  <button onClick={() => removeFile(type, idx)} className="text-gray-400 hover:text-red-500 transition-colors">
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="w-full flex flex-col gap-8 h-full p-10 min-h-[500px]">
      {renderDropzone(
        'questionPaper',
        'Question Paper',
        'Upload the blank exam paper.',
        'PDF, PNG, JPG'
      )}
      {renderDropzone(
        'answerKey',
        'Answer Key',
        'Upload the correct answers/guide.',
        'PDF, TXT, DOCX'
      )}
    </div>
  );
}
