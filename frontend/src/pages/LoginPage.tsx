import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { setUser } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';
import { Sparkles, Eye, EyeOff, Loader2, FileText, Users } from 'lucide-react';

const SAMPLE_USERS = [
  {
    label: 'Business Analyst',
    username: 'ba_user',
    password: 'ba123',
    description: 'Generate & submit deliverables',
    icon: FileText,
    gradient: 'from-cyan-500/20 to-blue-500/20',
    border: 'border-cyan-500/30 hover:border-cyan-400/60',
    badge: 'bg-cyan-500/20 text-cyan-300',
    name: 'Rama',
  },
  {
    label: 'Reviewer',
    username: 'reviewer',
    password: 'rev123',
    description: 'Approve or reject deliverables',
    icon: Users,
    gradient: 'from-violet-500/20 to-purple-500/20',
    border: 'border-violet-500/30 hover:border-violet-400/60',
    badge: 'bg-violet-500/20 text-violet-300',
    name: 'Badri',
  },
];

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeCard, setActiveCard] = useState<string | null>(null);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;
    setLoading(true);
    try {
      const user = await api.login(username, password);
      setUser(user);
      navigate('/');
    } catch {
      toast({
        title: 'Login failed',
        description: 'Invalid username or password. Try the sample accounts below.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const fillCredentials = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setActiveCard(u);
  };

  return (
    <div className="min-h-screen bg-[#0a0f1e] flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Logo & Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/25 mb-4">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-white tracking-tight">Idea2Spec</h1>
          <p className="text-slate-400 mt-2 text-sm">From Idea to Specification</p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-700/60 rounded-2xl p-8 shadow-2xl shadow-black/40">
          <h2 className="text-lg font-semibold text-white mb-1">Welcome back</h2>
          <p className="text-slate-400 text-sm mb-6">Sign in to your account to continue</p>

          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 uppercase tracking-wider">Username</label>
              <Input
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter your username"
                className="bg-slate-800/60 border-slate-600/60 text-white placeholder:text-slate-500 focus:border-cyan-500/60 focus:ring-cyan-500/20 h-11 rounded-xl"
                autoComplete="username"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 uppercase tracking-wider">Password</label>
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="bg-slate-800/60 border-slate-600/60 text-white placeholder:text-slate-500 focus:border-cyan-500/60 focus:ring-cyan-500/20 h-11 rounded-xl pr-11"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full h-11 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold shadow-lg shadow-cyan-500/20 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Signing in...</>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-slate-700/60" />
            <span className="text-xs text-slate-500 font-medium">SAMPLE ACCOUNTS</span>
            <div className="flex-1 h-px bg-slate-700/60" />
          </div>

          {/* Sample account cards */}
          <div className="grid grid-cols-2 gap-3">
            {SAMPLE_USERS.map(u => {
              const Icon = u.icon;
              const isActive = activeCard === u.username;
              return (
                <button
                  key={u.username}
                  type="button"
                  onClick={() => fillCredentials(u.username, u.password)}
                  className={`
                    relative text-left p-4 rounded-xl border transition-all duration-200
                    bg-gradient-to-br ${u.gradient} ${u.border}
                    ${isActive ? 'ring-1 ring-cyan-400/40 scale-[1.02]' : 'hover:scale-[1.01]'}
                  `}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${u.badge}`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    {isActive && (
                      <span className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">Selected</span>
                    )}
                  </div>
                  <div className="text-sm font-semibold text-white">{u.name} · {u.label}</div>
                  <div className="text-xs text-slate-400 mt-0.5 leading-tight">{u.description}</div>
                  <div className="mt-2 pt-2 border-t border-slate-700/40">
                    <code className="text-[11px] text-slate-400">
                      {u.username} / {u.password}
                    </code>
                  </div>
                </button>
              );
            })}
          </div>

          <p className="text-center text-xs text-slate-600 mt-5">
            Click a card to auto-fill credentials, then sign in
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-slate-600 mt-6">
          © 2025 Idea2Spec · Transform Ideas into Specifications
        </p>
      </div>
    </div>
  );
}
