import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { getUser, clearUser } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import {
  CheckCircle, XCircle, Clock, ArrowLeft, LogOut, User,
  Info, Loader2, ShieldCheck,
} from 'lucide-react';

const TYPE_LABELS: Record<string, string> = {
  brd: 'BRD', frd: 'FRD', user_stories: 'User Stories', test_cases: 'Test Cases',
  migration_plan: 'Migration Plan', reverse_eng: 'Reverse Engineering',
  tdd: 'Technical Design', db_analysis: 'DB Analysis',
};


export default function ReviewerPage() {
  const user = getUser();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string | null>(null);
  const [humanComments, setHumanComments] = useState<Record<string, string>>({});


  const handleLogout = () => { clearUser(); navigate('/login'); };

  const { data: pending = [], isLoading } = useQuery({
    queryKey: ['pending-reviews'],
    queryFn: () => api.getPendingReviews(),
    refetchInterval: 5000, // poll every 5s for AI review completion
  });

  const decisionMutation = useMutation({
    mutationFn: ({ reviewId, decision }: { reviewId: string; decision: 'sign_off' | 'return_to_ba' }) =>
      api.humanReviewDecision(reviewId, user!.id, decision, humanComments[reviewId] || '', {}),
    onSuccess: (_, vars) => {
      toast({
        title: vars.decision === 'sign_off' ? '✅ Accepted' : '↩ Returned to BA',
        description: vars.decision === 'sign_off' ? 'Deliverable accepted.' : 'Feedback sent to BA.',
      });
      queryClient.invalidateQueries({ queryKey: ['pending-reviews'] });
      setSelected(null);
    },
    onError: () => toast({ title: 'Error', description: 'Failed to save decision', variant: 'destructive' }),
  });

  const selectedReview = pending.find((r: any) => r.id === selected);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card shadow-soft">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
              <ArrowLeft className="w-4 h-4 mr-1" /> Dashboard
            </Button>
            <h1 className="text-lg font-semibold">Review Queue</h1>
            {pending.length > 0 && (
              <span className="text-xs bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 px-2 py-0.5 rounded-full">
                {pending.length} pending
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <div className="text-sm text-muted-foreground">
              <div className="font-medium text-foreground">{user?.full_name}</div>
              <div className="text-xs">Reviewer</div>
            </div>
            <Button variant="ghost" size="sm" onClick={handleLogout}><LogOut className="w-4 h-4" /></Button>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-6">
        {isLoading && (
          <div className="flex items-center justify-center py-16 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin mr-2" /> Loading reviews...
          </div>
        )}

        {!isLoading && pending.length === 0 && (
          <div className="text-center py-16 text-muted-foreground bg-card border rounded-xl">
            <ShieldCheck className="w-10 h-10 mx-auto mb-3 text-green-500/50" />
            No deliverables pending review.
          </div>
        )}

        {!isLoading && pending.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: queue list */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Pending Items</p>
              {pending.map((r: any) => (
                <button
                  key={r.id}
                  onClick={() => setSelected(r.id)}
                  className={`w-full text-left p-4 rounded-xl border transition-all ${
                    selected === r.id
                      ? 'border-cyan-500/50 bg-cyan-500/5'
                      : 'border-border bg-card hover:border-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-sm">{TYPE_LABELS[r.analysis_type] || r.analysis_type}</span>
                    <span className="text-xs text-slate-500"><Clock className="w-3 h-3 inline mr-1" />Pending</span>
                  </div>
                  <div className="text-xs text-muted-foreground">{r.project_name}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    v{r.version} · {r.submitted_at ? new Date(r.submitted_at).toLocaleString() : '—'}
                  </div>
                </button>
              ))}
            </div>

            {/* Right: detail panel */}
            <div className="lg:col-span-2">
              {!selectedReview ? (
                <div className="flex items-center justify-center h-64 text-muted-foreground border border-dashed rounded-xl">
                  Select a review item to begin
                </div>
              ) : (
                <div className="space-y-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-lg font-semibold">{TYPE_LABELS[selectedReview.analysis_type] || selectedReview.analysis_type}</h2>
                      <p className="text-sm text-muted-foreground">{selectedReview.project_name} · Version {selectedReview.version}</p>
                    </div>
                    {selectedReview.checklist?.length > 0 && (
                      <div className="text-xs text-slate-400 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 max-w-xs">
                        <p className="font-semibold mb-1">BA Checklist:</p>
                        {selectedReview.checklist.map((item: string, i: number) => (
                          <div key={i} className="flex items-center gap-1"><Info className="w-3 h-3" />{item}</div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Reviewer commentary */}
                  <div className="bg-card border rounded-xl p-4 space-y-3">
                    <p className="text-sm font-semibold flex items-center gap-2">
                      <User className="w-4 h-4 text-violet-400" /> Your Commentary (optional)
                    </p>
                    <Textarea
                      placeholder="Add your own observations, context, or additional feedback for the BA..."
                      value={humanComments[selectedReview.id] || ''}
                      onChange={e => setHumanComments(p => ({ ...p, [selectedReview.id]: e.target.value }))}
                      className="bg-slate-800/60 border-slate-600 text-white resize-none"
                      rows={4}
                    />
                  </div>

                  {/* Decision buttons */}
                  <div className="flex gap-3">
                    <Button
                      className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                      onClick={() => decisionMutation.mutate({ reviewId: selectedReview.id, decision: 'sign_off' })}
                      disabled={decisionMutation.isPending}
                    >
                      {decisionMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                      Accept
                    </Button>
                    <Button
                      variant="destructive"
                      className="flex-1"
                      onClick={() => decisionMutation.mutate({ reviewId: selectedReview.id, decision: 'return_to_ba' })}
                      disabled={decisionMutation.isPending}
                    >
                      {decisionMutation.isPending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <XCircle className="w-4 h-4 mr-2" />}
                      Return to BA
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
