import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Database, Layout, RefreshCw, Plus, Loader2, FolderOpen } from "lucide-react";
import { useEffect, useState } from "react";
import { api, Project } from "@/lib/api";

interface AnalysisOptionsStepProps {
  data: any;
  updateData: (data: any) => void;
}

export const AnalysisOptionsStep = ({ data, updateData }: AnalysisOptionsStepProps) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);

  // Load existing projects when append mode is selected
  useEffect(() => {
    if (data.mode === 'append') {
      loadProjects();
    }
  }, [data.mode]);

  const loadProjects = async () => {
    setLoadingProjects(true);
    try {
      const projectList = await api.listProjects({ limit: 100 });
      setProjects(projectList.filter(p => p.status === 'ready'));
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoadingProjects(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <Label className="text-base font-semibold">Analysis Features</Label>
        <div className="space-y-4 mt-4">
          <Card className="p-4 border-2">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Database className="w-5 h-5 text-primary" />
                </div>
                <div className="flex-1">
                  <Label htmlFor="db-introspection" className="text-base font-medium">
                    Database Introspection
                  </Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Analyze database schema, stored procedures, and relationships. Requires
                    connection string or DB dump.
                  </p>
                </div>
              </div>
              <Switch
                id="db-introspection"
                checked={data.includeDbIntrospection || false}
                onCheckedChange={(checked) =>
                  updateData({ includeDbIntrospection: checked })
                }
              />
            </div>
          </Card>

          <Card className="p-4 border-2">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0">
                  <Layout className="w-5 h-5 text-accent" />
                </div>
                <div className="flex-1">
                  <Label htmlFor="ui-parsing" className="text-base font-medium">
                    UI/Frontend Parsing
                  </Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Parse and analyze frontend code to understand user interface structure and
                    components.
                  </p>
                </div>
              </div>
              <Switch
                id="ui-parsing"
                checked={data.includeUiParsing || false}
                onCheckedChange={(checked) => updateData({ includeUiParsing: checked })}
              />
            </div>
          </Card>
        </div>
      </div>

      <div className="border-t pt-6">
        <Label className="text-base font-semibold">Indexing Mode</Label>
        <RadioGroup
          value={data.mode || "initial"}
          onValueChange={(value) => updateData({ mode: value })}
          className="mt-4 space-y-3"
        >
          <Card className="p-4 border-2">
            <div className="flex items-center space-x-3">
              <RadioGroupItem value="initial" id="initial" />
              <Label htmlFor="initial" className="flex items-center gap-3 cursor-pointer flex-1">
                <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center flex-shrink-0">
                  <Plus className="w-5 h-5 text-success" />
                </div>
                <div>
                  <p className="font-medium">Initial Load</p>
                  <p className="text-sm text-muted-foreground">
                    Build a fresh knowledge base from scratch. Recommended for new projects.
                  </p>
                </div>
              </Label>
            </div>
          </Card>

          <Card className={`p-4 border-2 ${data.mode === 'append' ? 'border-warning' : ''}`}>
            <div className="flex items-center space-x-3">
              <RadioGroupItem value="append" id="append" />
              <Label htmlFor="append" className="flex items-center gap-3 cursor-pointer flex-1">
                <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center flex-shrink-0">
                  <RefreshCw className="w-5 h-5 text-warning" />
                </div>
                <div>
                  <p className="font-medium">Append/Incremental Mode</p>
                  <p className="text-sm text-muted-foreground">
                    Add new changes to existing knowledge base. Use for updates to existing
                    projects.
                  </p>
                </div>
              </Label>
            </div>

            {/* Project selector - shown when append mode is selected */}
            {data.mode === 'append' && (
              <div className="mt-4 ml-6 pl-7 border-l-2 border-warning/30">
                <Label className="text-sm font-medium mb-2 block">
                  Select Existing Project to Append To
                </Label>
                {loadingProjects ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading projects...
                  </div>
                ) : projects.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-2">
                    No existing projects found. Please create a project first with Initial Load.
                  </p>
                ) : (
                  <Select
                    value={data.appendToProjectId || ''}
                    onValueChange={(value) => {
                      const selectedProject = projects.find(p => p.id === value);
                      updateData({ 
                        appendToProjectId: value,
                        appendToProjectName: selectedProject?.name 
                      });
                    }}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select a project..." />
                    </SelectTrigger>
                    <SelectContent>
                      {projects.map((project) => (
                        <SelectItem key={project.id} value={project.id}>
                          <div className="flex items-center gap-2">
                            <FolderOpen className="w-4 h-4 text-muted-foreground" />
                            <span>{project.name}</span>
                            <span className="text-xs text-muted-foreground">
                              ({project.file_count} files)
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
                {data.appendToProjectId && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Files from Step 2 will be added to "{data.appendToProjectName}"
                  </p>
                )}
              </div>
            )}
          </Card>
        </RadioGroup>
      </div>
    </div>
  );
};
