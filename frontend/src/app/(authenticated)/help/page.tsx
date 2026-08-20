"use client";

import React from "react";
import { HelpCircle, BookOpen, FileCheck, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function HelpPage() {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-display text-xl flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-slate-800" /> Examiner Help & Documentation
          </h1>
          <p className="text-caption text-xs">
            Understanding deterministic rubric arithmetic, value-point matching, and examiner verification rules.
          </p>
        </div>
        <Badge variant="academic">Documentation</Badge>
      </div>

      <div className="space-y-4 text-xs text-slate-700">
        <div className="calm-card p-5 space-y-2">
          <h3 className="text-heading text-sm font-bold flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-slate-800" /> Deterministic Core vs LLM Language Layer
          </h3>
          <p className="text-body text-xs leading-relaxed text-slate-600">
            GradeMIND derives numeric marks strictly through deterministic rubric arithmetic over extracted evidence. The LLM extracts, paraphrases, classifies, and explains — but is never the sole authority on awarded marks.
          </p>
        </div>

        <div className="calm-card p-5 space-y-2">
          <h3 className="text-heading text-sm font-bold flex items-center gap-2">
            <FileCheck className="h-4 w-4 text-slate-800" /> Traceable Criterion Evidence
          </h3>
          <p className="text-body text-xs leading-relaxed text-slate-600">
            Every mark awarded is linked to (a) marking-scheme criterion ID, (b) character span in student answer text, and (c) model engine provenance version.
          </p>
        </div>

        <div className="calm-card p-5 space-y-2">
          <h3 className="text-heading text-sm font-bold flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-teal-600" /> Anonymization & DPDP Act 2023 Compliance
          </h3>
          <p className="text-body text-xs leading-relaxed text-slate-600">
            Student names and roll numbers are masked before evaluation text reaches the scoring engines, preventing bias in marking.
          </p>
        </div>
      </div>
    </div>
  );
}
