import { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import {
  FileText, Download, RefreshCw, DollarSign, Clock,
  CheckCircle2, Play, Loader2, Lock, MessageSquare, ThumbsUp, AlertTriangle,
} from "lucide-react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { api, Analysis, AnalysisProgress, downloadFile } from "@/lib/api";
import { getUser, isBA, isReviewer } from "@/lib/auth";
import { useToast } from "@/hooks/use-toast";

interface DeliverablesTabProps {
  projectId: string;
}

const formatEta = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
};

const OTHER_DELIVERABLES = [
  { type: "reverse_eng", name: "Reverse Engineering Document" },
  { type: "brd", name: "Business Requirements (BRD)" },
  { type: "frd", name: "Functional Requirements (FRD)" },
  { type: "tdd", name: "Technical Design (TDD)" },
  { type: "db_analysis", name: "Database Analysis & ER Diagrams" },
  { type: "test_cases", name: "Test Cases" },
  { type: "migration_plan", name: "Migration Plan" },
];

const DEFAULT_MODEL = "gemini-3-pro-preview";

const MODEL_OPTIONS = [
  { value: "gemini-3-pro-preview", label: "Gemini 3 Pro Preview" },
];

export const DeliverablesTab = ({ projectId }: DeliverablesTabProps) => {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const [progress, setProgress] = useState<Record<string, AnalysisProgress>>({});
  const [smeFeedback, setSmeFeedback] = useState("");
  const [userStoriesConfirmed, setUserStoriesConfirmed] = useState(false);
  // timestamp (ms) of last user stories regeneration — deliverables generated before this are stale
  const [usRegenAt, setUsRegenAt] = useState<number | null>(null);
  const [selectedModels, setSelectedModels] = useState<Record<string, string>>({});
  const [reviewStatuses, setReviewStatuses] = useState<Record<string, any>>({});
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [reviewModal, setReviewModal] = useState<{ analysisId: string; type: string; mode: 'accept' | 'return' } | null>(null);
  const [reviewComment, setReviewComment] = useState("");
  const [reviewDeciding, setReviewDeciding] = useState(false);
  const progressIntervalRef = useRef<Record<string, NodeJS.Timeout>>({});
  const { toast } = useToast();

  useEffect(() => {
    loadAnalyses();
    // restore regen timestamp from localStorage
    const ts = localStorage.getItem(`us_regenerated_${projectId}`);
    if (ts) setUsRegenAt(parseInt(ts));
    return () => { Object.values(progressIntervalRef.current).forEach(clearInterval); };
  }, [projectId]);

  const loadReviewStatus = async (analysisId: string, type: string) => {
    try {
      const review = await api.getReviewByAnalysis(analysisId);
      if (review) setReviewStatuses(prev => ({ ...prev, [type]: review }));
    } catch { /* ignore */ }
  };

  const handleReviewDecision = async (decision: 'sign_off' | 'return_to_ba') => {
    if (!reviewModal) return;
    const user = getUser();
    if (!user) return;
    setReviewDeciding(true);
    try {
      const review = reviewStatuses[reviewModal.type];
      if (!review) throw new Error('No review found');
      await api.humanReviewDecision(review.id, user.id, decision, decision === 'return_to_ba' ? reviewComment : '', {});
      toast({
        title: decision === 'sign_off' ? '✅ Accepted' : '↩ Returned to BA',
        description: decision === 'sign_off' ? 'Deliverable accepted.' : 'Feedback sent to BA.',
      });
      await loadReviewStatus(reviewModal.analysisId, reviewModal.type);
      setReviewModal(null);
      setReviewComment("");
    } catch {
      toast({ title: "Error", description: "Failed to save decision", variant: "destructive" });
    } finally {
      setReviewDeciding(false);
    }
  };

  const handleSubmitForReview = async (analysisId: string, type: string) => {
    const user = getUser();
    if (!user) return;
    setSubmitting(type);
    try {
      await api.submitForReview(analysisId, projectId, user.id, []);
      toast({ title: "Submitted for Review", description: "AI Reviewer is analysing. Reviewer will be notified." });
      await loadReviewStatus(analysisId, type);
    } catch {
      toast({ title: "Error", description: "Failed to submit for review", variant: "destructive" });
    } finally {
      setSubmitting(null);
    }
  };

  const loadAnalyses = async () => {
    try {
      const data = await api.listAnalyses(projectId);
      setAnalyses(data);
      const alreadyConfirmed = localStorage.getItem(`us_confirmed_${projectId}`) === "true";
      if (alreadyConfirmed) setUserStoriesConfirmed(true);
      data.forEach((analysis) => {
        if (analysis.status === "in-progress") {
          startProgressPolling(analysis.analysis_id, analysis.analysis_type);
        }
        if (analysis.status === "complete" || analysis.status === "partial") {
          loadReviewStatus(analysis.analysis_id, analysis.analysis_type);
        }
      });
    } catch (error) {
      console.error("Error loading analyses:", error);
    } finally {
      setLoading(false);
    }
  };

  const startProgressPolling = (analysisId: string, analysisType: string) => {
    if (progressIntervalRef.current[analysisType]) {
      clearInterval(progressIntervalRef.current[analysisType]);
    }
    const poll = async () => {
      try {
        const p = await api.getAnalysisProgress(analysisId);
        setProgress((prev) => ({ ...prev, [analysisType]: p }));
        if (p.status === "complete" || p.status === "failed" || p.status === "partial") {
          clearInterval(progressIntervalRef.current[analysisType]);
          delete progressIntervalRef.current[analysisType];
          setGenerating(null);
          const refreshed = await api.listAnalyses(projectId);
          setAnalyses(refreshed);
          const alreadyConfirmed = localStorage.getItem(`us_confirmed_${projectId}`) === "true";
          if (alreadyConfirmed) setUserStoriesConfirmed(true);

        }
      } catch (e) { console.error("Error polling progress:", e); }
    };
    poll();
    progressIntervalRef.current[analysisType] = setInterval(poll, 2000);
  };

  const handleGenerate = async (type: string, model: string) => {
    setGenerating(type);
    try {
      const analysis = await api.runAnalysis(projectId, type, model);
      toast({ title: "Analysis Started", description: "Generating... watch the progress below." });
      startProgressPolling(analysis.analysis_id, type);
    } catch (error) {
      toast({ title: "Error", description: error instanceof Error ? error.message : "Failed to generate", variant: "destructive" });
      setGenerating(null);
    }
  };

  const handleRegenerate = async (analysisId: string, type: string, model: string, feedback?: string) => {
    setGenerating(type);
    try {
      const analysis = await api.regenerateAnalysis(analysisId, model, feedback);
      toast({ title: "Regeneration Started", description: "Regenerating with your feedback..." });
      if (type === "user_stories") {
        setSmeFeedback("");
        // Reset confirmation — all other deliverables are now stale
        setUserStoriesConfirmed(false);
        localStorage.removeItem(`us_confirmed_${projectId}`);
        const now = Date.now();
        localStorage.setItem(`us_regenerated_${projectId}`, now.toString());
        setUsRegenAt(now);
      }
      startProgressPolling(analysis.analysis_id, type);
    } catch (error) {
      toast({ title: "Error", description: error instanceof Error ? error.message : "Failed to regenerate", variant: "destructive" });
      setGenerating(null);
    }
  };

  const handleConfirmUserStories = () => {
    setUserStoriesConfirmed(true);
    localStorage.setItem(`us_confirmed_${projectId}`, "true");
    // Clear stale marker once user re-confirms
    localStorage.removeItem(`us_regenerated_${projectId}`);
    setUsRegenAt(null);
    toast({ title: "User Stories Confirmed", description: "All other deliverables are now unlocked." });
  };

  const handleDownload = async (analysisId: string, format: "word" | "markdown" | "html", type: string) => {
    try {
      const blob = await api.downloadAnalysis(analysisId, format);
      const ext = format === "word" ? "docx" : format === "html" ? "html" : "md";
      downloadFile(blob, `${type}_${analysisId}.${ext}`);
    } catch (error) {
      toast({ title: "Error", description: "Failed to download file", variant: "destructive" });
    }
  };

  // A deliverable is stale if it was generated BEFORE the last user stories regeneration
  const isStale = (deliverable: Analysis | undefined): boolean => {
    if (!deliverable || !usRegenAt) return false;
    const generatedAt = new Date(deliverable.created_at).getTime();
    return generatedAt < usRegenAt;
  };

  const getModel = (type: string) => selectedModels[type] || DEFAULT_MODEL;
  const getAnalysisForType = (type: string) => analyses.find(a => a.analysis_type === type);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "complete": return "bg-success/10 text-success";
      case "partial": return "bg-warning/10 text-warning";
      case "in-progress": return "bg-primary/10 text-primary";
      case "failed": return "bg-destructive/10 text-destructive";
      default: return "bg-muted text-muted-foreground";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "complete": return CheckCircle2;
      case "partial": return FileText;
      case "in-progress": return RefreshCw;
      default: return Clock;
    }
  };

  const renderProgressBar = (type: string) => {
    const currentProgress = progress[type];
    if (!currentProgress || generating !== type) return null;
    return (
      <div className="mb-4 p-3 bg-muted/50 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">{currentProgress.message}</span>
          <div className="flex items-center gap-3">
            {currentProgress.eta_seconds != null && currentProgress.eta_seconds > 0 && (
              <span className="text-sm text-muted-foreground flex items-center gap-1">
                <Clock className="w-3 h-3" />~{formatEta(currentProgress.eta_seconds)} remaining
              </span>
            )}
            <span className="text-sm text-muted-foreground">
              Step {currentProgress.current_step} of {currentProgress.total_steps}
            </span>
          </div>
        </div>
        <Progress value={currentProgress.percent_complete} className="h-2 mb-2" />
        <div className="text-xs text-muted-foreground">
          {currentProgress.current_section !== "complete" && currentProgress.current_section !== "initializing" && (
            <span>Generating: <span className="text-primary font-medium">{currentProgress.current_section}</span></span>
          )}
          {currentProgress.completed_sections.length > 0 && (
            <span className="ml-2">
              • Completed: {currentProgress.completed_sections.slice(-3).join(", ")}
              {currentProgress.completed_sections.length > 3 && ` (+${currentProgress.completed_sections.length - 3} more)`}
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderReviewStatus = (analysisId: string, type: string) => {
    const review = reviewStatuses[type];
    // BA: only show status if submitted; Reviewer: only show if submitted
    if (!review) return null;
    const isReturned = review.status === 'returned';
    const isApproved = review.status === 'approved';

    return (
      <div className="mt-3 space-y-2">
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium ${
          isApproved ? 'bg-green-500/10 text-green-400 border-green-500/20'
          : isReturned ? 'bg-red-500/10 text-red-400 border-red-500/20'
          : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
        }`}>
          {isApproved ? <CheckCircle2 className="w-4 h-4" /> : isReturned ? <MessageSquare className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
          {isApproved ? 'Accepted' : isReturned ? 'Returned — Feedback below' : 'Pending Review'}
          {review.version > 1 && <span className="text-xs opacity-70">v{review.version}</span>}
          {/* Reviewer action buttons — only shown to reviewer, only when pending/returned */}
          {isReviewer() && !isApproved && (
            <div className="ml-auto flex gap-1.5">
              <Button
                size="sm"
                className="bg-green-600 hover:bg-green-700 text-white h-6 text-xs px-2"
                onClick={() => { setReviewModal({ analysisId, type, mode: 'accept' }); setReviewComment(""); }}
              >
                <CheckCircle2 className="w-3 h-3 mr-1" />Accept
              </Button>
              <Button
                size="sm"
                variant="destructive"
                className="h-6 text-xs px-2"
                onClick={() => { setReviewModal({ analysisId, type, mode: 'return' }); setReviewComment(""); }}
              >
                Return to BA
              </Button>
            </div>
          )}
        </div>
        {/* BA sees reviewer's comment when returned */}
        {isReturned && review.human_comments && (
          <div className="p-3 rounded-lg bg-red-500/5 border border-red-500/20 text-xs">
            <p className="font-semibold text-red-400 mb-1">Reviewer Comment:</p>
            <p className="text-muted-foreground">{review.human_comments}</p>
          </div>
        )}
      </div>
    );
  };

  const renderSubmitButton = (deliverable: Analysis, type: string) => {
    if (!isBA()) return null;
    const review = reviewStatuses[type];
    // Hide if approved or currently in AI/human review
    if (review && (review.status === 'approved' || review.status === 'ai_reviewing' || review.status === 'pending_human')) return null;
    const isSubmitting = submitting === type;
    const isResubmit = review?.status === 'returned';
    return (
      <div className="mt-3 space-y-2">
        <Button
          size="sm"
          variant="outline"
          className="border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10"
          onClick={() => handleSubmitForReview(deliverable.analysis_id, type)}
          disabled={isSubmitting}
        >
          {isSubmitting ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : <MessageSquare className="w-4 h-4 mr-1" />}
          {isResubmit ? 'Resubmit for Review' : 'Submit for Review'}
        </Button>
      </div>
    );
  };

  const renderDownloadButtons = (deliverable: Analysis, type: string) => {
    const isGenerating = generating === type;
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => handleDownload(deliverable.analysis_id, "word", type)} disabled={isGenerating}>
          <Download className="w-4 h-4 mr-1" />.docx
        </Button>
        <Button variant="outline" size="sm" onClick={() => handleDownload(deliverable.analysis_id, "markdown", type)} disabled={isGenerating}>
          <Download className="w-4 h-4 mr-1" />.md
        </Button>
        <Button variant="outline" size="sm" onClick={() => handleDownload(deliverable.analysis_id, "html", type)} disabled={isGenerating}>
          <Download className="w-4 h-4 mr-1" />.html
        </Button>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const userStoriesAnalysis = getAnalysisForType("user_stories");
  const isUSGenerating = generating === "user_stories";
  const usStatus = userStoriesAnalysis?.status || "pending";
  const USStatusIcon = getStatusIcon(usStatus);

  return (
    <div className="space-y-4">
      {/* ── USER STORIES CARD ── */}
      <Card className="p-6 shadow-medium border-2 border-primary/30">
        <div className="flex items-start gap-4">
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${getStatusColor(usStatus)}`}>
            <FileText className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-lg">User Stories</h4>
                <Badge variant="outline" className="text-xs text-primary border-primary/40">Required First</Badge>
              </div>
              <div className="flex items-center gap-2">
                <Badge className={getStatusColor(usStatus)}>
                  <USStatusIcon className="w-3 h-3 mr-1" />
                  {usStatus}
                </Badge>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              Generate and confirm user stories before unlocking other deliverables.
            </p>

            {renderProgressBar("user_stories")}

            {usStatus === "partial" && !isUSGenerating && (
              <div className="mb-3 p-3 bg-warning/10 border border-warning/20 rounded-lg text-sm text-warning">
                Partial document available — some sections were generated. You can download or regenerate.
              </div>
            )}

            {userStoriesAnalysis && usStatus !== "pending" && !isUSGenerating && (
              <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
                <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{new Date(userStoriesAnalysis.created_at).toLocaleString()}</span>
                {userStoriesAnalysis.cost && (
                  <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />${userStoriesAnalysis.cost.toFixed(2)}</span>
                )}
                {userStoriesAnalysis.model && <Badge variant="outline" className="text-xs">{userStoriesAnalysis.model}</Badge>}
              </div>
            )}

            {/* Generate (first time) */}
            {usStatus === "pending" && (
              <div className="flex items-center gap-2 mb-4">
                <Select value={getModel("user_stories")} onValueChange={(v) => setSelectedModels(p => ({ ...p, user_stories: v }))}>
                  <SelectTrigger className="w-52" disabled={isUSGenerating}><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {MODEL_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Button className="gradient-primary text-primary-foreground" onClick={() => handleGenerate("user_stories", getModel("user_stories"))} disabled={isUSGenerating}>
                  {isUSGenerating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                  {isUSGenerating ? "Generating..." : "Generate"}
                </Button>
              </div>
            )}

            {/* Download buttons */}
            {userStoriesAnalysis && usStatus !== "pending" && !isUSGenerating && (
              <div className="mb-4">{renderDownloadButtons(userStoriesAnalysis, "user_stories")}</div>
            )}

            {/* SME Feedback + Confirm — shown once generated, until confirmed, BA only */}
            {isBA() && userStoriesAnalysis && (usStatus === "complete" || usStatus === "partial") && !userStoriesConfirmed && (
              <div className="mt-4 p-4 bg-muted/40 rounded-lg border border-border space-y-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-primary" />
                  <span className="text-sm font-medium">SME Feedback</span>
                  <span className="text-xs text-muted-foreground">(optional)</span>
                </div>
                <Textarea
                  placeholder="e.g. Add a story for password reset flow. The admin role should also be able to export reports..."
                  value={smeFeedback}
                  onChange={(e) => setSmeFeedback(e.target.value)}
                  className="min-h-24 text-sm"
                  disabled={isUSGenerating}
                />
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRegenerate(userStoriesAnalysis.analysis_id, "user_stories", userStoriesAnalysis.model || DEFAULT_MODEL, smeFeedback)}
                    disabled={isUSGenerating}
                  >
                    {isUSGenerating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RefreshCw className="w-4 h-4 mr-2" />}
                    {isUSGenerating ? "Regenerating..." : "Regenerate with Feedback"}
                  </Button>
                </div>
                <div className="pt-1 border-t border-border">
                  <Button
                    className="gradient-primary text-primary-foreground w-full"
                    size="sm"
                    onClick={handleConfirmUserStories}
                  >
                    <ThumbsUp className="w-4 h-4 mr-2" />
                    Confirm User Stories &amp; Unlock All Deliverables
                  </Button>
                </div>
              </div>
            )}

            {/* Confirmed banner */}
            {userStoriesConfirmed && (
              <div className="mt-3 flex items-center gap-2 p-3 bg-success/10 border border-success/20 rounded-lg">
                <CheckCircle2 className="w-4 h-4 text-success" />
                <span className="text-sm text-success font-medium">User Stories confirmed — all deliverables unlocked</span>
                {isBA() && userStoriesAnalysis && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="ml-auto"
                    onClick={() => handleRegenerate(userStoriesAnalysis.analysis_id, "user_stories", userStoriesAnalysis.model || DEFAULT_MODEL)}
                    disabled={isUSGenerating}
                  >
                    {isUSGenerating ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <RefreshCw className="w-3 h-3 mr-1" />}
                    Regenerate
                  </Button>
                )}
              </div>
            )}

            {/* Submit for Review (User Stories) */}
            {userStoriesAnalysis && (usStatus === "complete" || usStatus === "partial") && !isUSGenerating && (
              <div className="mt-3">
                {renderSubmitButton(userStoriesAnalysis, "user_stories")}
                {renderReviewStatus(userStoriesAnalysis.analysis_id, "user_stories")}
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* ── OTHER DELIVERABLES ── */}
      {OTHER_DELIVERABLES.map((deliverableType) => {
        const deliverable = getAnalysisForType(deliverableType.type);
        const status = deliverable?.status || "pending";
        const StatusIcon = getStatusIcon(status);
        const isGenerating = generating === deliverableType.type;
        const locked = !userStoriesConfirmed;
        const stale = isStale(deliverable);

        return (
          <div key={deliverableType.type} className={`relative transition-all duration-300 ${locked ? "opacity-50" : ""}`}>
            {locked && (
              <div className="absolute inset-0 z-10 rounded-xl flex items-center justify-center backdrop-blur-[2px] bg-background/30">
                <div className="flex items-center gap-2 px-4 py-2 bg-card border rounded-full shadow-medium">
                  <Lock className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Confirm User Stories to unlock</span>
                </div>
              </div>
            )}
            <Card className="p-6 shadow-medium hover:shadow-strong transition-smooth">
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${getStatusColor(status)}`}>
                  <FileText className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-semibold text-lg">{deliverableType.name}</h4>
                    <Badge className={getStatusColor(status)}>
                      <StatusIcon className="w-3 h-3 mr-1" />{status}
                    </Badge>
                  </div>

                  {renderProgressBar(deliverableType.type)}

                  {/* Stale warning — user stories were regenerated after this deliverable was generated */}
                  {stale && !isGenerating && (
                    <div className="mb-3 p-3 bg-warning/10 border border-warning/20 rounded-lg flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-warning mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm text-warning font-medium">User Stories were updated</p>
                        <p className="text-xs text-warning/80 mt-0.5">This document was generated from the previous version. Regenerate to align with the latest user stories.</p>
                      </div>
                      <Button
                        size="sm"
                        className="gradient-primary text-primary-foreground flex-shrink-0"
                        onClick={() => handleRegenerate(deliverable!.analysis_id, deliverableType.type, deliverable!.model || DEFAULT_MODEL)}
                        disabled={isGenerating}
                      >
                        <RefreshCw className="w-3 h-3 mr-1" />
                        Regenerate
                      </Button>
                    </div>
                  )}

                  {deliverable && status === "partial" && !isGenerating && !stale && (
                    <div className="mb-3 p-3 bg-warning/10 border border-warning/20 rounded-lg text-sm text-warning">
                      Partial document available. Download or regenerate.
                    </div>
                  )}

                  {deliverable && status !== "pending" && !isGenerating && (
                    <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                      <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{new Date(deliverable.created_at).toLocaleString()}</span>
                      {deliverable.cost && <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />${deliverable.cost.toFixed(2)}</span>}
                      {deliverable.model && <Badge variant="outline" className="text-xs">{deliverable.model}</Badge>}
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    {status === "pending" ? (
                      <>
                        <Select
                          value={getModel(deliverableType.type)}
                          onValueChange={(v) => setSelectedModels(p => ({ ...p, [deliverableType.type]: v }))}
                          disabled={locked || isGenerating}
                        >
                          <SelectTrigger className="w-52"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {MODEL_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                          </SelectContent>
                        </Select>
                        <Button
                          className="gradient-primary text-primary-foreground"
                          onClick={() => handleGenerate(deliverableType.type, getModel(deliverableType.type))}
                          disabled={locked || isGenerating}
                        >
                          {isGenerating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                          {isGenerating ? "Generating..." : "Generate"}
                        </Button>
                      </>
                    ) : (
                      deliverable && !stale && renderDownloadButtons(deliverable, deliverableType.type)
                    )}
                  </div>
                  {deliverable && renderReviewStatus(deliverable.analysis_id, deliverableType.type)}
                </div>
              </div>
            </Card>
          </div>
        );
      })}
      {/* ── REVIEWER MODAL ── */}
      <Dialog open={!!reviewModal} onOpenChange={(open) => { if (!open) { setReviewModal(null); setReviewComment(""); } }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{reviewModal?.mode === 'accept' ? 'Accept Deliverable' : 'Return to BA'}</DialogTitle>
          </DialogHeader>
          <div className="py-2">
            {reviewModal?.mode === 'accept' ? (
              <p className="text-sm text-muted-foreground">Are you sure you want to accept this deliverable?</p>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Add a comment for the BA explaining what needs to be changed.</p>
                <Textarea
                  placeholder="Your comment for the BA..."
                  value={reviewComment}
                  onChange={e => setReviewComment(e.target.value)}
                  className="resize-none"
                  rows={4}
                  autoFocus
                />
              </div>
            )}
          </div>
          <DialogFooter>
            {reviewModal?.mode === 'accept' ? (
              <Button
                className="w-full bg-green-600 hover:bg-green-700 text-white"
                onClick={() => handleReviewDecision('sign_off')}
                disabled={reviewDeciding}
              >
                {reviewDeciding ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
                Confirm Accept
              </Button>
            ) : (
              <Button
                variant="destructive"
                className="w-full"
                onClick={() => handleReviewDecision('return_to_ba')}
                disabled={reviewDeciding || !reviewComment.trim()}
              >
                {reviewDeciding ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <MessageSquare className="w-4 h-4 mr-2" />}
                Send to BA
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
