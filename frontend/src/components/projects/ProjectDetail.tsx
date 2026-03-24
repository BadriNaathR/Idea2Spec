import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Settings, Loader2, Sparkles } from "lucide-react";
import { OverviewTab } from "./detail/OverviewTab";
import { DeliverablesTab } from "./detail/DeliverablesTab";
import { ChatTab } from "./detail/ChatTab";
import { InsightsTab } from "./detail/InsightsTab";
import { api, Project } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("overview");
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    if (projectId) {
      loadProject();
      // Poll for status updates if project is processing
      const interval = setInterval(() => {
        if (project?.status === "processing" || project?.status === "pending") {
          loadProject();
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [projectId, project?.status]);

  const loadProject = async () => {
    if (!projectId) return;
    
    try {
      const data = await api.getProject(projectId);
      setProject(data);
    } catch (error) {
      console.error('Error loading project:', error);
      toast({
        title: "Error",
        description: "Failed to load project details",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Project not found</p>
          <Button onClick={() => navigate("/")}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card shadow-soft sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                onClick={() => navigate("/")}
                size="sm"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Dashboard
              </Button>
              <div className="flex items-center gap-2 pl-2 border-l">
                <div className="w-6 h-6 rounded-md gradient-primary flex items-center justify-center">
                  <Sparkles className="w-3 h-3 text-primary-foreground" />
                </div>
                <span className="text-sm font-semibold text-foreground">Idea2Spec</span>
              </div>
            </div>
            <Button variant="outline" size="sm">
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </div>
          <div>
            <h1 className="text-2xl font-bold mb-1">{project.name}</h1>
            <p className="text-sm text-muted-foreground">{project.description}</p>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 mb-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="deliverables">Deliverables</TabsTrigger>
            <TabsTrigger value="chat">Chat Assistant</TabsTrigger>
            <TabsTrigger value="insights">Insights</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <OverviewTab project={project} onProjectUpdate={loadProject} />
          </TabsContent>

          <TabsContent value="deliverables">
            <DeliverablesTab projectId={project.id!} />
          </TabsContent>

          <TabsContent value="chat">
            <ChatTab projectId={project.id!} />
          </TabsContent>

          <TabsContent value="insights">
            <InsightsTab projectId={project.id!} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};
