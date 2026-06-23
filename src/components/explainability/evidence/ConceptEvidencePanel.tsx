'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ConceptEvidencePanelProps } from './types';
import { ChevronRight } from 'lucide-react';

export default function ConceptEvidencePanel({ concepts, selectedConceptId, onSelect }: ConceptEvidencePanelProps) {
  return (
    <div className="w-full h-full overflow-y-auto pr-2 space-y-3 custom-scrollbar">
      <h3 className="text-xl font-bold text-gray-900 mb-6 sticky top-0 bg-white pt-2 pb-4 z-10">
        Evaluated Concepts
      </h3>
      
      {concepts.map((concept) => {
        const isSelected = concept.id === selectedConceptId;
        
        return (
          <motion.div
            key={concept.id}
            layout
            onClick={() => onSelect(concept.id)}
            className={`
              relative p-5 rounded-2xl cursor-pointer transition-colors border
              ${isSelected 
                ? 'bg-brand-secondary/30 border-brand-primary/40' 
                : 'bg-white border-gray-100 hover:border-brand-primary/30'}
            `}
          >
            {isSelected && (
              <motion.div
                layoutId="active-indicator"
                className="absolute left-0 top-0 bottom-0 w-1.5 bg-brand-primary rounded-l-2xl"
                initial={false}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              />
            )}
            
            <div className="flex justify-between items-start mb-3">
              <h4 className={`text-base font-bold pr-4 ${isSelected ? 'text-brand-primary' : 'text-gray-800'}`}>
                {concept.name}
              </h4>
              <div className="flex flex-col items-end shrink-0">
                <span className="text-sm font-extrabold text-gray-900">{concept.score}/{concept.maxScore}</span>
              </div>
            </div>

            <div className="flex items-center justify-between mt-4">
              <span className="text-xs font-medium text-gray-500">
                Confidence: <span className="font-bold">{concept.confidence}%</span>
              </span>
              <div className="flex items-center text-brand-primary text-sm font-semibold">
                View Evidence <ChevronRight className="w-4 h-4 ml-1" />
              </div>
            </div>
            
            <AnimatePresence>
              {isSelected && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-4 pt-4 border-t border-brand-primary/10 overflow-hidden"
                >
                  <p className="text-sm text-gray-700 leading-relaxed">
                    {concept.explanation}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </div>
  );
}
