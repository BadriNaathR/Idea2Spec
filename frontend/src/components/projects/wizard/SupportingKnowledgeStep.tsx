import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FileText, Upload, Trash2, BookOpen } from "lucide-react";

interface SupportingKnowledgeStepProps {
  data: any;
  updateData: (data: any) => void;
}

export const SupportingKnowledgeStep = ({
  data,
  updateData,
}: SupportingKnowledgeStepProps) => {
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      updateData({ adHocContent: text, userStoryFile: file.name });
    };
    reader.readAsText(file);
  };

  const clearFile = () => {
    updateData({ adHocContent: "", userStoryFile: null });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 p-4 rounded-lg bg-primary/5 border border-primary/20">
        <BookOpen className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-sm font-medium text-foreground">User Stories Input</p>
          <p className="text-xs text-muted-foreground mt-1">
            Provide your initial user stories or requirements. These will be used to generate
            and refine the User Stories deliverable before other documents are unlocked.
          </p>
        </div>
      </div>

      {/* File Upload */}
      <div>
        <Label className="text-sm font-medium">Upload User Stories File</Label>
        <p className="text-xs text-muted-foreground mt-1 mb-3">
          Upload a .txt, .md, or .docx file containing your user stories or requirements
        </p>
        <div className="p-5 border-2 border-dashed rounded-lg hover:border-primary transition-smooth">
          {data.userStoryFile ? (
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                <FileText className="w-4 h-4 text-primary" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">{data.userStoryFile}</p>
                <p className="text-xs text-muted-foreground">Content loaded into text area below</p>
              </div>
              <Button variant="ghost" size="icon" onClick={clearFile}>
                <Trash2 className="w-4 h-4 text-destructive" />
              </Button>
            </div>
          ) : (
            <label className="flex flex-col items-center gap-2 cursor-pointer">
              <Upload className="w-8 h-8 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Click to upload or drag & drop</span>
              <span className="text-xs text-muted-foreground">.txt, .md, .csv files</span>
              <Input
                type="file"
                accept=".txt,.md,.csv"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          )}
        </div>
      </div>

      {/* Text Input */}
      <div>
        <Label htmlFor="user-stories-text">Or Paste User Stories / Requirements</Label>
        <Textarea
          id="user-stories-text"
          placeholder={`Paste your user stories here. For example:\n\nAs a customer, I want to log in with my email so that I can access my account.\nAs an admin, I want to view all users so that I can manage access.\n\nOr describe the features and requirements in plain text...`}
          value={data.adHocContent || ""}
          onChange={(e) => updateData({ adHocContent: e.target.value })}
          className="mt-2 min-h-48 font-mono text-sm"
        />
        <p className="text-xs text-muted-foreground mt-2">
          {(data.adHocContent || "").length} characters · You can refine these further in the Deliverables tab after project creation
        </p>
      </div>
    </div>
  );
};
