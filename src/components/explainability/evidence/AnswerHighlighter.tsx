'use client';

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { AnswerHighlighterProps } from './types';

export default function AnswerHighlighter({ fullText, evidenceRegions, activeConceptId }: AnswerHighlighterProps) {
  
  // Combine regions and sort to chunk the text
  const chunks = useMemo(() => {
    if (!evidenceRegions || evidenceRegions.length === 0) {
      return [{ text: fullText, isHighlighted: false }];
    }

    // Sort by start index
    const sorted = [...evidenceRegions].sort((a, b) => a.start - b.start);
    const result: { text: string; isHighlighted: boolean }[] = [];
    
    let currentIndex = 0;

    for (const region of sorted) {
      // Catch up to the region
      if (region.start > currentIndex) {
        result.push({
          text: fullText.substring(currentIndex, region.start),
          isHighlighted: false
        });
      }

      // Add highlighted region
      // In case regions overlap, we strictly slice from the fullText
      result.push({
        text: fullText.substring(Math.max(currentIndex, region.start), region.end),
        isHighlighted: true
      });

      currentIndex = Math.max(currentIndex, region.end);
    }

    // Add remainder
    if (currentIndex < fullText.length) {
      result.push({
        text: fullText.substring(currentIndex),
        isHighlighted: false
      });
    }

    return result;
  }, [fullText, evidenceRegions]);

  return (
    <div className="w-full text-lg lg:text-xl text-gray-800 leading-relaxed lg:leading-loose whitespace-pre-wrap font-medium">
      {chunks.map((chunk, index) => (
        <motion.span
          key={`${activeConceptId}-${index}`}
          initial={{ backgroundColor: chunk.isHighlighted ? 'rgba(252, 211, 77, 0)' : 'transparent' }}
          animate={{ backgroundColor: chunk.isHighlighted ? 'rgba(252, 211, 77, 0.4)' : 'transparent' }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className={chunk.isHighlighted ? "rounded-md px-1 -mx-1 text-gray-900 font-bold border-b-2 border-brand-primary" : ""}
        >
          {chunk.text}
        </motion.span>
      ))}
    </div>
  );
}
