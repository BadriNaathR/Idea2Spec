import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ArrowLeft, ArrowRight, Check, Loader2 } from "lucide-react";
import { BasicInfoStep } from "./wizard/BasicInfoStep";
import { SourceInputsStep } from "./wizard/SourceInputsStep";
import { SupportingKnowledgeStep } from "./wizard/SupportingKnowledgeStep";
import { AnalysisOptionsStep } from "./wizard/AnalysisOptionsStep";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/lib/api";

export interface ProjectData {
  name: string;
  description: string;
  domain: string;
  tags: string[];
  environment: string;
  sourceType: "zip" | "files" | "scm";
  scmProvider?: "github" | "azure" | "bitbucket";
  scmRepo?: string;
  files: File[];
  supportingDocs: Array<{
    file: File;
    type: string;
    priority: string;
  }>;
  adHocContent: string;
  includeDbIntrospection: boolean;
  includeUiParsing: boolean;
  mode: "initial" | "append";
  appendToProjectId?: string;
  appendToProjectName?: string;
}

const steps = [
  { id: 1, name: "Basic Info", description: "Project details" },
  { id: 2, name: "Source Inputs", description: "Code & repositories" },
  { id: 3, name: "User Stories", description: "Requirements input" },
  { id: 4, name: "Analysis Options", description: "Configuration" },
];

export const ProjectWizard = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [projectData, setProjectData] = useState<Partial<ProjectData>>({
    tags: [],
    files: [],
    supportingDocs: [],
    includeDbIntrospection: false,
    includeUiParsing: false,
    mode: "initial",
  });
  const navigate = useNavigate();
  const { toast } = useToast();

  const updateProjectData = (data: Partial<ProjectData>) => {
    setProjectData((prev) => ({ ...prev, ...data }));
  };

  const handleNext = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleFinish = async () => {
    setIsSubmitting(true);
    
    try {
      // Check if we're in append mode with a selected project
      if (projectData.mode === 'append' && projectData.appendToProjectId) {
        // Append files to existing project
        if (!projectData.files || projectData.files.length === 0) {
          toast({
            title: "No Files",
            description: "Please select files to add to the project.",
            variant: "destructive",
          });
          setIsSubmitting(false);
          return;
        }

        await api.addFilesToProject(projectData.appendToProjectId, projectData.files, {
          supportingDocs: projectData.supportingDocs,
          adHocContent: projectData.adHocContent,
        });

        toast({
          title: "Files Added",
          description: `${projectData.files.length} file(s) are being added to "${projectData.appendToProjectName}".`,
        });
        
        // Navigate to the existing project
        navigate(`/projects/${projectData.appendToProjectId}`);
      } else {
        // Create new project (Initial Load mode)
        const createData = {
          name: projectData.name!,
          description: projectData.description,
          domain: projectData.domain,
          tags: projectData.tags?.join(','),
          environment: projectData.environment,
          source_type: projectData.sourceType || 'files',
          scm_provider: projectData.scmProvider,
          scm_repo: projectData.scmRepo,
          scm_branch: 'main',
          files: projectData.files,
          indexing_mode: projectData.mode || 'initial',
          include_db_introspection: projectData.includeDbIntrospection,
          include_ui_parsing: projectData.includeUiParsing,
          supporting_docs: projectData.supportingDocs,
          ad_hoc_content: projectData.adHocContent,
        };

        // Create project via API
        const project = await api.createProject(createData);

        toast({
          title: "Project Created",
          description: `${project.name} has been created successfully.`,
        });
        
        // Navigate to the newly created project
        navigate(`/projects/${project.id}`);
      }
    } catch (error) {
      console.error('Error:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to complete operation. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const progress = (currentStep / steps.length) * 100;

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return <BasicInfoStep data={projectData} updateData={updateProjectData} />;
      case 2:
        return <SourceInputsStep data={projectData} updateData={updateProjectData} />;
      case 3:
        return <SupportingKnowledgeStep data={projectData} updateData={updateProjectData} />;
      case 4:
        return <AnalysisOptionsStep data={projectData} updateData={updateProjectData} />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="container max-w-5xl mx-auto px-6">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={() => navigate("/")}
            className="mb-4 -ml-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-bold mb-2">Create New Project</h1>
          <p className="text-muted-foreground">
            Set up your application modernization project
          </p>
        </div>

        {/* Progress Steps */}
        <div className="mb-8">
          <Progress value={progress} className="h-2 mb-6" />
          <div className="grid grid-cols-4 gap-4">
            {steps.map((step) => (
              <div
                key={step.id}
                className={`flex items-start gap-3 ${
                  step.id <= currentStep ? "opacity-100" : "opacity-40"
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-smooth ${
                    step.id < currentStep
                      ? "bg-success text-success-foreground"
                      : step.id === currentStep
                      ? "gradient-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {step.id < currentStep ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <span className="text-sm font-semibold">{step.id}</span>
                  )}
                </div>
                <div className="hidden md:block">
                  <p className="font-medium text-sm">{step.name}</p>
                  <p className="text-xs text-muted-foreground">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <Card className="p-8 shadow-medium mb-6">{renderStep()}</Card>

        {/* Navigation */}
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={currentStep === 1}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Previous
          </Button>
          {currentStep < steps.length ? (
            <Button onClick={handleNext} className="gradient-primary text-primary-foreground">
              Next
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          ) : (
            <Button 
              onClick={handleFinish} 
              className="gradient-primary text-primary-foreground"
              disabled={isSubmitting || (projectData.mode === 'append' && !projectData.appendToProjectId)}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {projectData.mode === 'append' ? 'Adding Files...' : 'Creating Project...'}
                </>
              ) : (
                <>
                  <Check className="w-4 h-4 mr-2" />
                  {projectData.mode === 'append' ? 'Add Files to Project' : 'Create Project'}
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
