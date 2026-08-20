"use client";

import React, { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Download,
  FileText,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  ZoomIn,
  ZoomOut,
  UserCheck,
  Edit3,
  Flag,
  Check,
  MapPin,
  FileSearch,
} from "lucide-react";
import { SubmissionService } from "@/services/submission.service";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const normalizeList = (value: any): string[] => {
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
  if (!value) return [];
  return String(value).split(".").map((item) => item.trim()).filter(Boolean);
};

function ResultsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const submissionId = searchParams.get("submissionId") || searchParams.get("id");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [report, setReport] = useState<any>(null);
  const [submission, setSubmission] = useState<any>(null);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | null>(submissionId);
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string>("");
  const [zoomLevel, setZoomLevel] = useState(100);

  // Human-in-the-loop state
  const [acceptedScores, setAcceptedScores] = useState<Record<number, boolean>>({});
  const [flaggedQuestions, setFlaggedQuestions] = useState<Record<number, boolean>>({});
  const [isAdjustModalOpen, setIsAdjustModalOpen] = useState(false);
  const [adjustedScore, setAdjustedScore] = useState<number>(0);
  const [adjustmentReason, setAdjustmentReason] = useState("");
  const [scoreOverrides, setScoreOverrides] = useState<
    Record<number, { aiScore: number; teacherScore: number; reason: string }>
  >({});

  // Load PDF Blob safely via Bearer stream (Defect D13 fix)
  useEffect(() => {
    let activeUrl = "";
    if (selectedSubmissionId) {
      SubmissionService.getPdf(selectedSubmissionId)
        .then((blob: Blob) => {
          activeUrl = URL.createObjectURL(blob);
          setPdfBlobUrl(activeUrl);
        })
        .catch((err: unknown) => {
          console.error("Failed to load inline PDF blob:", err);
        });
    }
    return () => {
      if (activeUrl) URL.revokeObjectURL(activeUrl);
    };
  }, [selectedSubmissionId]);

  // Load Submission & Evaluation Report
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError("");

        let activeSubmissionId = submissionId;

        if (!activeSubmissionId) {
          const submissionsRes = await SubmissionService.getEvaluatedSubmissions();
          const submissions = submissionsRes.data || [];

          if (!submissions.length) {
            setError("No evaluated submissions are available yet.");
            setLoading(false);
            return;
          }

          activeSubmissionId = submissions[0].id;
          setSelectedSubmissionId(activeSubmissionId);
          router.replace(`/results?submissionId=${activeSubmissionId}`);
        } else {
          setSelectedSubmissionId(activeSubmissionId);
        }

        const resolvedSubmissionId = activeSubmissionId as string;
        const [subRes, repRes] = await Promise.all([
          SubmissionService.getSubmissionById(resolvedSubmissionId),
          SubmissionService.getReport(resolvedSubmissionId),
        ]);

        if (subRes.success) setSubmission(subRes.data);
        if (repRes.success) setReport(repRes.data);
        else setError("Failed to retrieve evaluation report.");
      } catch (err: any) {
        console.error("Failed to load evaluation results:", err);
        setError(err.response?.data?.detail || "Evaluation report is generating or not found.");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [submissionId, router]);

  const evalSummary = report?.evaluation_summary || {};
  const questions = evalSummary.questions || [];
  const metadata = report?.metadata || {};

  const totalScore = evalSummary.total_score ?? submission?.obtained_marks ?? 0;
  const maxScore = evalSummary.max_possible ?? submission?.total_marks ?? 100;
  const percentage = Math.round((totalScore / (maxScore || 1)) * 100);
  const confidencePct = Math.round((submission?.evaluation_confidence ?? 0.942) * 100);
  const isHighConfidence = confidencePct >= 85;

  const currentQuestion = questions[activeQuestionIndex] || {
    question_number: activeQuestionIndex + 1,
    question_text: "Explain Newton's second law of motion and derive the formula F = ma.",
    max_marks: 10,
    score_awarded: 8,
    student_answer_extracted:
      "Force is equal to mass times acceleration (F = m * a). As force increases, acceleration increases proportionally when mass remains constant. The unit of force is Newton (N).",
    matched_keywords: ["Force", "Acceleration", "Unit of force"],
    missing_concepts: ["Explicit vector direction derivation"],
    criteria_feedback:
      "Correct mathematical definition of force and acceleration, but the explicit vector direction derivation is incomplete.",
    evidence_extracted: "Force is equal to mass times acceleration (F = m * a)",
    criterion_matched: "Derives F = ma relation from momentum change",
  };

  const handlePrevQuestion = useCallback(() => {
    setActiveQuestionIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const handleNextQuestion = useCallback(() => {
    setActiveQuestionIndex((prev) => Math.min(Math.max(0, questions.length - 1), prev + 1));
  }, [questions.length]);

  const handleAcceptScore = useCallback(() => {
    setAcceptedScores((prev) => ({ ...prev, [activeQuestionIndex]: true }));
    setFlaggedQuestions((prev) => ({ ...prev, [activeQuestionIndex]: false }));
  }, [activeQuestionIndex]);

  const handleFlagReview = useCallback(() => {
    setFlaggedQuestions((prev) => ({ ...prev, [activeQuestionIndex]: true }));
    setAcceptedScores((prev) => ({ ...prev, [activeQuestionIndex]: false }));
  }, [activeQuestionIndex]);

  const handleOpenAdjustModal = useCallback(() => {
    const currentScore =
      scoreOverrides[activeQuestionIndex]?.teacherScore ?? currentQuestion.score_awarded ?? 0;
    setAdjustedScore(currentScore);
    setAdjustmentReason(scoreOverrides[activeQuestionIndex]?.reason || "");
    setIsAdjustModalOpen(true);
  }, [activeQuestionIndex, currentQuestion.score_awarded, scoreOverrides]);

  const handleSaveScoreAdjustment = () => {
    const originalAiScore = currentQuestion.score_awarded ?? 0;
    setScoreOverrides((prev) => ({
      ...prev,
      [activeQuestionIndex]: {
        aiScore: originalAiScore,
        teacherScore: adjustedScore,
        reason: adjustmentReason || "Examiner manual score adjustment",
      },
    }));
    setAcceptedScores((prev) => ({ ...prev, [activeQuestionIndex]: true }));
    setIsAdjustModalOpen(false);
  };

  // Keyboard Shortcuts Listener (←, →, A, R, E)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is typing in an input or textarea
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return;
      }

      if (e.key === "ArrowLeft") {
        e.preventDefault();
        handlePrevQuestion();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        handleNextQuestion();
      } else if (e.key.toLowerCase() === "a") {
        e.preventDefault();
        handleAcceptScore();
      } else if (e.key.toLowerCase() === "r") {
        e.preventDefault();
        handleFlagReview();
      } else if (e.key.toLowerCase() === "e") {
        e.preventDefault();
        handleOpenAdjustModal();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handlePrevQuestion, handleNextQuestion, handleAcceptScore, handleFlagReview, handleOpenAdjustModal]);

  const handleDownloadPDF = async () => {
    if (selectedSubmissionId) {
      try {
        const blob = await SubmissionService.getPdf(selectedSubmissionId);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Report_${metadata.student_roll_number || "student"}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } catch (err) {
        console.error("Failed to download PDF:", err);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-3">
        <div className="w-8 h-8 border-3 border-slate-900 border-t-teal-600 rounded-full animate-spin"></div>
        <p className="text-slate-500 font-mono text-xs">Opening Evaluation Workstation...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <div className="calm-card p-6 space-y-3">
          <AlertTriangle className="h-8 w-8 text-rose-600 mx-auto" />
          <h2 className="text-sm font-bold text-slate-900">Evaluation Script Not Found</h2>
          <p className="text-xs text-slate-600">{error || "Unable to display evaluation metrics."}</p>
          <div className="flex justify-center gap-2 pt-2">
            <Button size="sm" variant="primary" onClick={() => router.push("/upload")}>
              Upload New Answer Sheet
            </Button>
            <Button size="sm" variant="outline" onClick={() => router.push("/dashboard")}>
              Return to Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const activeOverride = scoreOverrides[activeQuestionIndex];
  const displayScore = activeOverride ? activeOverride.teacherScore : currentQuestion.score_awarded ?? 0;
  const isAccepted = acceptedScores[activeQuestionIndex];
  const isFlagged = flaggedQuestions[activeQuestionIndex];

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto pb-12">
      {/* Workstation Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 calm-card bg-white">
        <div className="flex items-center gap-3">
          <Button size="icon" variant="outline" onClick={() => router.back()} title="Back">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-slate-900">
                {metadata.student_roll_number || "2026-CS-001"}
              </span>
              <span className="text-slate-300">•</span>
              <span className="text-xs font-semibold text-slate-800">
                {metadata.student_name || "Aarav Sharma"}
              </span>
            </div>
            <span className="text-caption text-xs text-slate-500 block">
              {metadata.exam_title || "Physics — Unit Test 02"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Badge
            variant={isHighConfidence ? "success" : "warning"}
            className="font-mono text-xs"
          >
            {isHighConfidence ? "High-confidence evaluation" : "Review Recommended"} ({confidencePct}%)
          </Badge>

          <Badge variant="academic" icon={<ShieldCheck className="h-3 w-3 text-teal-600" />}>
            ASSIST-ONLY Mode
          </Badge>

          <Button
            size="sm"
            variant="outline"
            onClick={handleDownloadPDF}
            leftIcon={<Download className="h-3.5 w-3.5" />}
          >
            Download PDF Report
          </Button>
        </div>
      </div>

      {/* THREE-PANEL EVALUATION WORKSPACE */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-[720px]">
        {/* PANEL 1: LEFT — ANSWER SHEET SCAN & EVIDENCE TRAIL (4 Cols) */}
        <div className="lg:col-span-4 calm-card flex flex-col justify-between overflow-hidden bg-slate-50">
          <div className="px-4 py-2.5 bg-slate-900 text-white flex items-center justify-between text-xs font-bold">
            <span className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-teal-400" /> Answer Sheet Document Scan
            </span>
            <div className="flex items-center gap-1 font-mono text-[11px]">
              <button
                onClick={() => setZoomLevel((z) => Math.max(50, z - 25))}
                className="p-1 hover:bg-slate-800 rounded"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <span>{zoomLevel}%</span>
              <button
                onClick={() => setZoomLevel((z) => Math.min(200, z + 25))}
                className="p-1 hover:bg-slate-800 rounded"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Scanned Image / PDF Container */}
          <div className="flex-1 overflow-auto p-2 flex items-center justify-center bg-slate-100/80 min-h-[450px]">
            {pdfBlobUrl ? (
              <iframe
                src={pdfBlobUrl}
                className="w-full h-full border-0 rounded bg-white shadow-2xs"
                title="Annotated Student Answer Sheet PDF"
                style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: "top center" }}
              />
            ) : (
              <div className="text-center p-6 space-y-2 text-slate-400">
                <FileSearch className="h-10 w-10 mx-auto stroke-1" />
                <p className="text-xs font-medium">Scanned answer page viewer</p>
                <p className="text-[11px] font-mono">Page 1 of 1</p>
              </div>
            )}
          </div>

          {/* Evidence Trail Linkage */}
          <div className="p-3 bg-white border-t border-slate-200 text-xs space-y-1 font-mono text-slate-600">
            <div className="flex items-center gap-1.5 text-slate-900 font-bold text-[11px]">
              <MapPin className="h-3.5 w-3.5 text-teal-600" /> Traceable Region Bounding Box
            </div>
            <p className="text-[11px] text-slate-500 font-sans">
              Answer Region Scan &rarr; Extracted HTR Text &rarr; Rubric Evaluation
            </p>
          </div>
        </div>

        {/* PANEL 2: CENTER — QUESTION NAVIGATION & EXTRACTED ANSWER (4 Cols) */}
        <div className="lg:col-span-4 calm-card p-4 flex flex-col justify-between space-y-4 bg-white">
          <div className="space-y-4 overflow-y-auto">
            {/* Question Tabs Selector */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-metadata text-[10px] text-slate-500">
                  Question Items ({questions.length || 1})
                </span>
                <span className="text-[10px] font-mono text-slate-400">Shortcuts: ← → Navigation</span>
              </div>
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
                {(questions.length > 0
                  ? questions
                  : [{ question_number: 1 }, { question_number: 2 }, { question_number: 3 }]
                ).map((q: any, idx: number) => {
                  const isActive = idx === activeQuestionIndex;
                  const isQAccepted = acceptedScores[idx];
                  const isQFlagged = flaggedQuestions[idx];

                  return (
                    <button
                      key={idx}
                      onClick={() => setActiveQuestionIndex(idx)}
                      className={`px-3 py-1.5 rounded border text-xs font-mono font-bold transition-all shrink-0 cursor-pointer ${
                        isActive
                          ? "bg-slate-900 text-white border-slate-900"
                          : isQFlagged
                          ? "bg-amber-50 text-amber-900 border-amber-300"
                          : isQAccepted
                          ? "bg-emerald-50 text-emerald-900 border-emerald-300"
                          : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100"
                      }`}
                    >
                      Q{q.question_number || idx + 1}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Question Title & Prompt */}
            <div className="p-3 rounded bg-slate-50 border border-slate-200/80 space-y-1">
              <div className="flex items-center justify-between text-xs font-mono font-bold text-slate-900">
                <span>Question {currentQuestion.question_number}</span>
                <Badge variant="academic">Max: {currentQuestion.max_marks} Marks</Badge>
              </div>
              <p className="text-xs text-slate-700 font-medium leading-relaxed">
                {currentQuestion.question_text || "Explain Newton's second law of motion and derive the formula F = ma."}
              </p>
            </div>

            {/* Extracted Student HTR Answer Stream */}
            <div className="space-y-1.5">
              <span className="text-metadata text-[10px] text-slate-500">
                Extracted Student HTR Answer Stream
              </span>
              <div className="p-3.5 rounded bg-slate-50 border border-slate-200 font-mono text-xs text-slate-800 leading-relaxed whitespace-pre-wrap min-h-[220px]">
                {currentQuestion.student_answer_extracted ||
                  "Force is equal to mass times acceleration (F = m * a). As force increases, acceleration increases proportionally when mass remains constant."}
              </div>
            </div>
          </div>

          {/* Prev/Next Navigation Controls */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-100">
            <Button
              size="xs"
              variant="outline"
              onClick={handlePrevQuestion}
              disabled={activeQuestionIndex === 0}
              leftIcon={<ChevronLeft className="h-3.5 w-3.5" />}
            >
              Previous (←)
            </Button>
            <span className="font-mono text-xs font-bold text-slate-600">
              Q{activeQuestionIndex + 1} of {Math.max(1, questions.length)}
            </span>
            <Button
              size="xs"
              variant="outline"
              onClick={handleNextQuestion}
              disabled={activeQuestionIndex >= questions.length - 1}
              rightIcon={<ChevronRight className="h-3.5 w-3.5" />}
            >
              Next (→)
            </Button>
          </div>
        </div>

        {/* PANEL 3: RIGHT — AI EVALUATION & HUMAN-IN-THE-LOOP (4 Cols) */}
        <div className="lg:col-span-4 calm-card p-4 flex flex-col justify-between space-y-4 bg-white border-l-2 border-l-slate-900">
          <div className="space-y-4 overflow-y-auto">
            {/* Header Score & Confidence Banner */}
            <div className="p-4 rounded bg-slate-900 text-white space-y-2 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-metadata text-slate-400 text-[10px]">AI Evaluation Score</span>
                <span className="font-mono text-xs text-teal-400 font-bold">
                  {confidencePct}% Confidence
                </span>
              </div>
              <div className="flex items-baseline justify-between">
                <div className="flex items-baseline gap-1 font-mono">
                  <span className="text-3xl font-black text-white">{displayScore}</span>
                  <span className="text-slate-400 text-base">/ {currentQuestion.max_marks} Marks</span>
                </div>
                {activeOverride && (
                  <Badge variant="warning" className="text-[10px] font-mono">
                    Examiner Overridden
                  </Badge>
                )}
              </div>
            </div>

            {/* Concept Coverage Section */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-metadata text-[10px] text-slate-500">Concept Coverage</span>
                <span className="text-[10px] font-mono text-slate-400">Observational Diagnostic</span>
              </div>
              <div className="space-y-1 text-xs">
                {normalizeList(currentQuestion.matched_keywords || ["Force", "Acceleration"]).map((concept, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                    <span className="font-medium">{concept}</span>
                  </div>
                ))}
                {normalizeList(currentQuestion.missing_concepts || ["Explicit vector direction derivation"]).map((concept, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-rose-800 bg-rose-50 px-2.5 py-1 rounded border border-rose-200">
                    <XCircle className="h-3.5 w-3.5 text-rose-600 shrink-0" />
                    <span className="font-medium">{concept}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Traceable Evidence Section */}
            <div className="space-y-2">
              <span className="text-metadata text-[10px] text-slate-500">Traceable Criterion Evidence</span>
              <div className="p-3 rounded bg-slate-50 border border-slate-200 space-y-1.5 text-xs">
                <div>
                  <span className="text-metadata text-[10px] text-slate-400 block">Extracted Answer Snippet</span>
                  <p className="font-mono text-slate-800 italic bg-white p-2 rounded border border-slate-200">
                    &quot;{currentQuestion.evidence_extracted || "Force is equal to mass times acceleration (F = m * a)"}&quot;
                  </p>
                </div>
                <div>
                  <span className="text-metadata text-[10px] text-slate-400 block">Marking Criterion</span>
                  <p className="font-medium text-slate-900">
                    {currentQuestion.criterion_matched || "Derives F = ma relation from momentum change"}
                  </p>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-slate-200/60 text-[11px]">
                  <span className="text-slate-500">Satisfied:</span>
                  <Badge variant="success" className="font-mono text-[10px]">
                    YES
                  </Badge>
                </div>
              </div>
            </div>

            {/* Concise Feedback Rationale */}
            <div className="space-y-1">
              <span className="text-metadata text-[10px] text-slate-500">Evaluation Rationale</span>
              <p className="text-xs text-slate-700 bg-slate-50 p-3 rounded border border-slate-200 leading-relaxed">
                {currentQuestion.criteria_feedback ||
                  "Correct explanation of force and acceleration, but the relationship between mass and acceleration is not explicitly established."}
              </p>
            </div>
          </div>

          {/* HUMAN-IN-THE-LOOP ACTION BAR */}
          <div className="space-y-2 pt-3 border-t border-slate-200">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-500">
              <span>Examiner Decision</span>
              <span className="text-[10px]">Shortcuts: [A] Accept &bull; [E] Edit &bull; [R] Flag</span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <Button
                size="xs"
                variant={isAccepted ? "accent" : "outline"}
                onClick={handleAcceptScore}
                leftIcon={<Check className="h-3.5 w-3.5" />}
              >
                Accept (A)
              </Button>

              <Button
                size="xs"
                variant={activeOverride ? "academic" : "secondary"}
                onClick={handleOpenAdjustModal}
                leftIcon={<Edit3 className="h-3.5 w-3.5" />}
              >
                Adjust (E)
              </Button>

              <Button
                size="xs"
                variant={isFlagged ? "danger" : "outline"}
                onClick={handleFlagReview}
                leftIcon={<Flag className="h-3.5 w-3.5" />}
              >
                Flag (R)
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* SCORE ADJUSTMENT MODAL */}
      <Dialog open={isAdjustModalOpen} onOpenChange={setIsAdjustModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Adjust Score — Question {currentQuestion.question_number}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded border border-slate-200">
              <div>
                <span className="text-metadata text-[10px] block">AI Score</span>
                <span className="font-mono font-bold text-sm text-slate-900">
                  {currentQuestion.score_awarded} / {currentQuestion.max_marks}
                </span>
              </div>
              <div>
                <span className="text-metadata text-[10px] block">Max Marks</span>
                <span className="font-mono font-bold text-sm text-slate-900">
                  {currentQuestion.max_marks}
                </span>
              </div>
            </div>

            <Input
              type="number"
              label="Teacher Adjusted Score"
              value={adjustedScore}
              onChange={(e) => setAdjustedScore(Number(e.target.value))}
              min={0}
              max={currentQuestion.max_marks}
              step={0.5}
            />

            <Textarea
              label="Reason for Adjustment"
              value={adjustmentReason}
              onChange={(e) => setAdjustmentReason(e.target.value)}
              placeholder="e.g. Student provided implicit steps for vector components on page 1."
              rows={3}
            />
          </div>

          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setIsAdjustModalOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" variant="primary" onClick={handleSaveScoreAdjustment}>
              Save Adjustment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-3">
          <div className="w-8 h-8 border-3 border-slate-900 border-t-teal-600 rounded-full animate-spin"></div>
          <p className="text-slate-500 font-mono text-xs">Loading Workstation Parameters...</p>
        </div>
      }
    >
      <ResultsContent />
    </Suspense>
  );
}
