export interface EvidenceRegion {
  start: number;
  end: number;
  text: string;
}

export interface ConceptEvidence {
  id: string;
  name: string;
  score: number;
  maxScore: number;
  confidence: number;
  explanation: string;
  evidenceRegions: EvidenceRegion[];
}

export interface AnswerHighlighterProps {
  fullText: string;
  evidenceRegions: EvidenceRegion[];
  activeConceptId: string | null;
}

export interface ConceptEvidencePanelProps {
  concepts: ConceptEvidence[];
  selectedConceptId: string | null;
  onSelect: (id: string) => void;
}

export interface EvidenceViewerProps {
  fullText: string;
  concepts: ConceptEvidence[];
  isLoading?: boolean;
}
