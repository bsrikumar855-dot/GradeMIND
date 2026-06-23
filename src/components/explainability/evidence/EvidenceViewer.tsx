'use client';

import React, { useState, useEffect } from 'react';
import { EvidenceViewerProps, EvidenceRegion } from './types';
import ConceptEvidencePanel from './ConceptEvidencePanel';
import AnswerHighlighter from './AnswerHighlighter';
import EvidenceSkeleton from './EvidenceSkeleton';

export default function EvidenceViewer({ fullText, concepts, isLoading = false }: EvidenceViewerProps) {
  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(null);

  // Auto-select the first concept when concepts load
  useEffect(() => {
    if (concepts && concepts.length > 0 && !selectedConceptId) {
      setSelectedConceptId(concepts[0].id);
    }
  }, [concepts, selectedConceptId]);

  if (isLoading) {
    return <EvidenceSkeleton />;
  }

  if (!concepts || concepts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-64 bg-gray-50 rounded-[2rem] border border-gray-100">
        <p className="text-xl text-gray-500 font-semibold">No evidence data available.</p>
      </div>
    );
  }

  // Derive active regions
  const activeConcept = concepts.find(c => c.id === selectedConceptId);
  const activeRegions: EvidenceRegion[] = activeConcept?.evidenceRegions || [];

  return (
    <div className="w-full bg-white rounded-[2.5rem] p-6 lg:p-10 shadow-[0_24px_70px_rgba(47,90,58,0.06)] border border-gray-100 flex flex-col lg:flex-row gap-8 lg:gap-12 min-h-[600px]">
      
      {/* Left Sidebar: Concept Selection */}
      <div className="w-full lg:w-1/3 flex flex-col border-b lg:border-b-0 lg:border-r border-gray-100 pb-8 lg:pb-0 lg:pr-6 h-full max-h-[700px]">
        <ConceptEvidencePanel
          concepts={concepts}
          selectedConceptId={selectedConceptId}
          onSelect={setSelectedConceptId}
        />
      </div>

      {/* Right Content: Answer Highlight */}
      <div className="flex-1 flex flex-col h-full max-h-[700px] overflow-y-auto pr-4 custom-scrollbar">
        <div className="sticky top-0 bg-white pb-6 z-10 border-b border-gray-100 mb-6">
          <h2 className="text-2xl lg:text-3xl font-black text-brand-dark">
            Student Answer Evidence
          </h2>
          <p className="text-base text-gray-500 mt-2">
            Highlighted regions show exactly where the AI identified the selected concept.
          </p>
        </div>
        
        <div className="bg-gray-50/50 rounded-2xl p-6 lg:p-8 border border-gray-100">
          <AnswerHighlighter
            fullText={fullText}
            evidenceRegions={activeRegions}
            activeConceptId={selectedConceptId}
          />
        </div>
      </div>
    </div>
  );
}
