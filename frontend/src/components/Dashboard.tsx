import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { BarChart3, FileText, DollarSign, Plus, Folder, Loader2, Coins, Sparkles, LogOut, ClipboardList } from "lucide-react";
import { useState, useEffect } from "react";
import { MetricCard } from "./dashboard/MetricCard";
import { RecentActivity } from "./dashboard/RecentActivity";
import { api, Project, DashboardStats } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";
import { getUser, clearUser } from "@/lib/auth";

// Format large numbers (e.g., 1234567 -> "1.2M")
const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K';
  }
  return num.toString();
};

// Format cost (e.g., 182.5 -> "$182.50")
const formatCost = (cost: number): string => {
  if (cost >= 1000) {
    return '$' + formatNumber(cost);
  }
  return '$' + cost.toFixed(2).replace(/\.00$/, '');
};

export const Dashboard = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { toast } = useToast();
  const user = getUser();

  const handleLogout = () => {
    clearUser();
    navigate('/login');
  };

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [projectsData, statsData] = await Promise.all([
        api.listProjects({ limit: 10 }),
        api.getStats()
      ]);
      setProjects(projectsData);
      setStats(statsData);
    } catch (error) {
      console.error('Error loading data:', error);
      toast({
        title: "Error",
        description: "Failed to load data. Please check if the backend is running.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusLabel = (status: string) => {
    const statusMap: Record<string, string> = {
      'pending': 'Pending',
      'processing': 'Processing',
      'ready': 'Ready',
      'failed': 'Failed',
    };
    return statusMap[status] || status;
  };

  const getStatusColor = (status: string) => {
    const colorMap: Record<string, string> = {
      'pending': 'bg-yellow-500/10 text-yellow-600',
      'processing': 'bg-blue-500/10 text-blue-600',
      'ready': 'bg-green-500/10 text-green-600',
      'failed': 'bg-red-500/10 text-red-600',
    };
    return colorMap[status] || 'bg-primary/10 text-primary';
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card shadow-soft">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center shadow-medium">
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground tracking-tight">Idea2Spec</h1>
              <p className="text-xs text-muted-foreground">From Idea to Specification</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {user?.role === 'reviewer' && (
              <Button variant="outline" size="sm" onClick={() => navigate('/reviews')}>
                <ClipboardList className="w-4 h-4 mr-2" />Reviews
              </Button>
            )}
            {user?.role === 'business_analyst' && (
              <Button 
                onClick={() => navigate("/projects/new")}
                className="gradient-primary text-primary-foreground hover:opacity-90 transition-smooth"
              >
                <Plus className="w-4 h-4 mr-2" />
                New Project
              </Button>
            )}
            <div className="text-sm text-muted-foreground border-l pl-3">
              <div className="font-medium text-foreground">{user?.full_name}</div>
              <div className="text-xs capitalize">{user?.role?.replace('_', ' ')}</div>
            </div>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold mb-2">Welcome back, {user?.full_name?.split(' ')[0] || 'there'} 👋</h2>
          <p className="text-muted-foreground">Here's what's happening with your Idea2Spec projects</p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Applications"
            value={stats?.projects.total.toString() || projects.length.toString()}
            change={`+${stats?.projects.this_month || 0} this month`}
            icon={Folder}
            trend="up"
            iconColor="cyan"
          />
          <MetricCard
            title="Deliverables"
            value={stats?.deliverables.total.toString() || "0"}
            change={`+${stats?.deliverables.today || 0} today`}
            icon={FileText}
            trend="up"
            iconColor="blue"
          />
          <MetricCard
            title="Tokens Used"
            value={formatNumber(stats?.tokens.total || 0)}
            change={`${formatNumber(stats?.tokens.today || 0)} today`}
            icon={BarChart3}
            trend="neutral"
            iconColor="purple"
          />
          <MetricCard
            title="Total Cost"
            value={formatCost(stats?.cost.total || 0)}
            change={`${formatCost(stats?.cost.today || 0)} today`}
            icon={Coins}
            trend="up"
            iconColor="green"
          />
        </div>

        {/* Projects & Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2 p-6 shadow-medium hover:shadow-strong transition-smooth">
            <h3 className="text-lg font-semibold mb-4">Active Projects</h3>
            
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground mb-4">No projects yet</p>
                <Button onClick={() => navigate("/projects/new")} variant="outline">
                  <Plus className="w-4 h-4 mr-2" />
                  Create Your First Project
                </Button>
              </div>
            ) : (
              <div className="max-h-[400px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent hover:scrollbar-thumb-gray-400">
                <div className="space-y-3">
                  {projects.map((project) => (
                    <div 
                      key={project.id} 
                      onClick={() => navigate(`/projects/${project.id}`)}
                      className="p-4 rounded-lg bg-muted/50 hover:bg-muted transition-smooth cursor-pointer border border-gray-200"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-medium">{project.name}</h4>
                        <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(project.status)}`}>
                          {getStatusLabel(project.status)}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span>{project.file_count} files</span>
                        {project.domain && <span>• {project.domain}</span>}
                        {project.environment && <span>• {project.environment}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>

          <RecentActivity />
        </div>
      </main>
    </div>
  );
};
