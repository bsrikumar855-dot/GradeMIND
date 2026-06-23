import { ConceptEvidence } from './types';

export const MOCK_FULL_TEXT = `Photosynthesis is the process used by plants, algae and certain bacteria to harness energy from sunlight and turn it into chemical energy. The overall equation for photosynthesis is 6CO2 + 6H2O + light energy → C6H12O6 + 6O2. This process takes place in the chloroplasts, specifically using chlorophyll, the green pigment involved in capturing light energy.

The process is divided into two main stages: the light-dependent reactions and the Calvin cycle (light-independent reactions). In the light-dependent reactions, solar energy is absorbed by chlorophyll and converted into ATP and NADPH. Water molecules are split, releasing oxygen as a byproduct. In the Calvin cycle, ATP and NADPH are used to convert carbon dioxide into glucose, which the plant uses for growth and energy. 

I think cellular respiration is the exact opposite of this, where glucose is broken down to release energy.`;

export const MOCK_CONCEPT_EVIDENCE: ConceptEvidence[] = [
  {
    id: "concept-1",
    name: "Definition of Photosynthesis",
    score: 2,
    maxScore: 2,
    confidence: 96,
    explanation: "The student accurately defined photosynthesis as the conversion of light energy into chemical energy.",
    evidenceRegions: [
      { start: 0, end: 154, text: "Photosynthesis is the process used by plants, algae and certain bacteria to harness energy from sunlight and turn it into chemical energy." }
    ]
  },
  {
    id: "concept-2",
    name: "Chemical Equation",
    score: 3,
    maxScore: 3,
    confidence: 98,
    explanation: "The correct balanced chemical equation is provided.",
    evidenceRegions: [
      { start: 155, end: 251, text: "The overall equation for photosynthesis is 6CO2 + 6H2O + light energy → C6H12O6 + 6O2." }
    ]
  },
  {
    id: "concept-3",
    name: "Role of Chloroplasts",
    score: 2,
    maxScore: 2,
    confidence: 91,
    explanation: "Chloroplasts and chlorophyll are correctly identified as the site and pigment for light absorption.",
    evidenceRegions: [
      { start: 252, end: 388, text: "This process takes place in the chloroplasts, specifically using chlorophyll, the green pigment involved in capturing light energy." }
    ]
  },
  {
    id: "concept-4",
    name: "Light-Dependent Reactions",
    score: 3,
    maxScore: 4,
    confidence: 85,
    explanation: "Mentioned ATP, NADPH, and oxygen byproduct, but lacked detail on the exact mechanism of electron transport.",
    evidenceRegions: [
      { start: 504, end: 681, text: "In the light-dependent reactions, solar energy is absorbed by chlorophyll and converted into ATP and NADPH. Water molecules are split, releasing oxygen as a byproduct." }
    ]
  },
  {
    id: "concept-5",
    name: "Calvin Cycle",
    score: 3,
    maxScore: 4,
    confidence: 88,
    explanation: "Correctly identified that ATP and NADPH are used to fix carbon dioxide into glucose, though omitted RuBisCO.",
    evidenceRegions: [
      { start: 682, end: 818, text: "In the Calvin cycle, ATP and NADPH are used to convert carbon dioxide into glucose, which the plant uses for growth and energy." }
    ]
  }
];
