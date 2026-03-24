import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Lightbulb,
  Database,
  Code,
  Cloud,
  Loader2,
} from "lucide-react";
import { api, Insights } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface InsightsTabProps {
  projectId: string;
}

export const InsightsTab = ({ projectId }: InsightsTabProps) => {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    loadInsights();
  }, [projectId]);

  const loadInsights = async () => {
    try {
      const data = await api.getInsights(projectId);
      setInsights(data);
    } catch (error) {
      console.error('Error loading insights:', error);
      toast({
        title: "Error",
        description: "Failed to load insights",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No insights available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Modules */}
      <Card className="p-6 shadow-medium">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Code className="w-5 h-5 text-primary" />
          Code Hotspots
        </h3>
        <div className="space-y-3">
          {insights.code_hotspots.slice(0, 5).map((hotspot, idx) => (
            <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
              <div>
                <p className="font-medium">{hotspot.file_path}</p>
                <p className="text-sm text-muted-foreground">{hotspot.recommendation}</p>
              </div>
              <Badge variant={hotspot.complexity > 75 ? "destructive" : "secondary"}>
                Complexity: {hotspot.complexity}
              </Badge>
            </div>
          ))}
        </div>
      </Card>

      {/* DB Optimization */}
      <Card className="p-6 shadow-medium">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-accent" />
          Database Optimization Suggestions
        </h3>
        <div className="space-y-3">
          {insights.db_optimizations.map((optimization, idx) => {
            const IconComponent = optimization.impact === 'high' ? AlertCircle : Lightbulb;
            return (
              <div key={idx} className="flex items-start gap-3 p-4 rounded-lg border">
                <IconComponent className={`w-5 h-5 flex-shrink-0 mt-0.5 ${optimization.impact === 'high' ? 'text-warning' : 'text-primary'}`} />
                <div>
                  <p className="font-medium">{optimization.issue}</p>
                  <p className="text-sm text-muted-foreground mt-1">{optimization.recommendation}</p>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Modernization Recommendations */}
      <Card className="p-6 shadow-medium">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Cloud className="w-5 h-5 text-primary" />
          Technology Modernization Recommendations
        </h3>
        <div className="space-y-4">
          <div className="p-4 rounded-lg border-2 border-primary/20 bg-primary/5">
            <div className="flex items-start gap-3 mb-3">
              <TrendingUp className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-semibold">Microservices Architecture on AKS</h4>
                <p className="text-sm text-muted-foreground mt-1">
                  Identified 3 candidate services for decomposition
                </p>
              </div>
            </div>
            <div className="pl-8 space-y-2">
              <div className="flex items-center gap-2">
                <Badge variant="outline">Transaction Service</Badge>
                <span className="text-sm text-muted-foreground">Independent data & logic</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline">Report Service</Badge>
                <span className="text-sm text-muted-foreground">High compute, async</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline">Notification Service</Badge>
                <span className="text-sm text-muted-foreground">Event-driven</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-lg border">
            <h4 className="font-semibold mb-2">Recommended Tech Stack</h4>
            <div className="flex flex-wrap gap-2">
              <Badge>Azure Kubernetes Service</Badge>
              <Badge>Azure SQL Database</Badge>
              <Badge>Azure Service Bus</Badge>
              <Badge>Azure Functions</Badge>
              <Badge>Azure API Management</Badge>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
