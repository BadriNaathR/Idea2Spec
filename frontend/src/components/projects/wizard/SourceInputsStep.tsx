import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Upload, Github, FolderGit2, GitBranch, X, FileCode, File as FileIcon } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

interface SourceInputsStepProps {
  data: any;
  updateData: (data: any) => void;
}

// Common code file extensions
const CODE_FILE_EXTENSIONS = ".py,.js,.ts,.tsx,.jsx,.java,.cs,.cpp,.c,.h,.hpp,.go,.rb,.php,.swift,.kt,.scala,.rs,.sql,.json,.xml,.yaml,.yml,.md,.txt,.html,.css,.scss,.sass,.less,.vue,.svelte,.sh,.bash,.ps1,.bat,.dockerfile,.makefile,.gradle,.pom,.csproj,.sln,.config,.env,.gitignore,.properties";

const getFileIcon = (filename: string) => {
  const ext = filename.split('.').pop()?.toLowerCase();
  const codeExts = ['py', 'js', 'ts', 'tsx', 'jsx', 'java', 'cs', 'cpp', 'c', 'go', 'rb', 'php', 'swift', 'kt', 'rs'];
  return codeExts.includes(ext || '') ? FileCode : FileIcon;
};

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const SourceInputsStep = ({ data, updateData }: SourceInputsStepProps) => {
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      const existingFiles = data.files || [];
      // Merge new files, avoiding duplicates by name
      const existingNames = new Set(existingFiles.map((f: File) => f.name));
      const uniqueNewFiles = newFiles.filter(f => !existingNames.has(f.name));
      updateData({ files: [...existingFiles, ...uniqueNewFiles] });
    }
    // Reset input to allow selecting same file again
    e.target.value = '';
  };

  const removeFile = (index: number) => {
    const newFiles = [...(data.files || [])];
    newFiles.splice(index, 1);
    updateData({ files: newFiles });
  };

  const clearAllFiles = () => {
    updateData({ files: [] });
  };

  return (
    <div className="space-y-6">
      <div>
        <Label className="text-base font-semibold">Source Input Method</Label>
        <RadioGroup
          value={data.sourceType || "zip"}
          onValueChange={(value) => updateData({ sourceType: value })}
          className="mt-4 space-y-3"
        >
          <div className="flex items-center space-x-3 p-4 rounded-lg border hover:border-primary transition-smooth cursor-pointer">
            <RadioGroupItem value="zip" id="zip" />
            <Label htmlFor="zip" className="flex items-center gap-3 cursor-pointer flex-1">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Upload className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">Upload ZIP Archive</p>
                <p className="text-sm text-muted-foreground">
                  Upload a compressed repository snapshot
                </p>
              </div>
            </Label>
          </div>

          <div className="flex items-center space-x-3 p-4 rounded-lg border hover:border-primary transition-smooth cursor-pointer">
            <RadioGroupItem value="files" id="files" />
            <Label htmlFor="files" className="flex items-center gap-3 cursor-pointer flex-1">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <FolderGit2 className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">Upload Individual Files</p>
                <p className="text-sm text-muted-foreground">
                  Select specific code files and scripts
                </p>
              </div>
            </Label>
          </div>

          <div className="flex items-center space-x-3 p-4 rounded-lg border hover:border-primary transition-smooth cursor-pointer">
            <RadioGroupItem value="scm" id="scm" />
            <Label htmlFor="scm" className="flex items-center gap-3 cursor-pointer flex-1">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Github className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">Connect to SCM</p>
                <p className="text-sm text-muted-foreground">
                  GitHub, Azure Repos, or Bitbucket
                </p>
              </div>
            </Label>
          </div>
        </RadioGroup>
      </div>

      {data.sourceType === "zip" && (
        <div className="p-6 border-2 border-dashed rounded-lg hover:border-primary transition-smooth">
          <Input
            type="file"
            accept=".zip"
            onChange={handleFileUpload}
            className="cursor-pointer"
          />
          <p className="text-sm text-muted-foreground mt-2">
            Upload a ZIP file containing your source code
          </p>
          {data.files && data.files.length > 0 && (
            <div className="mt-3 p-3 bg-muted rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{data.files[0].name}</span>
                <Button variant="ghost" size="sm" onClick={() => updateData({ files: [] })}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <span className="text-xs text-muted-foreground">{formatFileSize(data.files[0].size)}</span>
            </div>
          )}
        </div>
      )}

      {data.sourceType === "files" && (
        <div className="space-y-4">
          <div className="p-6 border-2 border-dashed rounded-lg hover:border-primary transition-smooth">
            <Input
              type="file"
              multiple
              accept={CODE_FILE_EXTENSIONS}
              onChange={handleFileUpload}
              className="cursor-pointer"
            />
            <p className="text-sm text-muted-foreground mt-2">
              Select code files (.py, .js, .ts, .java, .cs, .sql, etc.)
            </p>
          </div>
          
          {data.files && data.files.length > 0 && (
            <div className="border rounded-lg">
              <div className="flex items-center justify-between p-3 border-b bg-muted/50">
                <span className="text-sm font-medium">
                  {data.files.length} file(s) selected
                </span>
                <Button variant="ghost" size="sm" onClick={clearAllFiles} className="text-destructive hover:text-destructive">
                  Clear All
                </Button>
              </div>
              <ScrollArea className="max-h-[200px]">
                <div className="p-2 space-y-1">
                  {data.files.map((file: File, idx: number) => {
                    const IconComponent = getFileIcon(file.name);
                    return (
                      <div 
                        key={idx} 
                        className="flex items-center justify-between p-2 rounded hover:bg-muted/50 group"
                      >
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <IconComponent className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span className="text-sm truncate">{file.name}</span>
                          <Badge variant="outline" className="text-xs flex-shrink-0">
                            {formatFileSize(file.size)}
                          </Badge>
                        </div>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => removeFile(idx)}
                          className="opacity-0 group-hover:opacity-100 h-6 w-6 p-0"
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>
            </div>
          )}
        </div>
      )}

      {data.sourceType === "scm" && (
        <div className="space-y-4">
          <div>
            <Label htmlFor="scm-provider">SCM Provider</Label>
            <Select
              value={data.scmProvider || ""}
              onValueChange={(value) => updateData({ scmProvider: value })}
            >
              <SelectTrigger className="mt-2">
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="github">
                  <div className="flex items-center gap-2">
                    <Github className="w-4 h-4" />
                    GitHub
                  </div>
                </SelectItem>
                <SelectItem value="azure">
                  <div className="flex items-center gap-2">
                    <GitBranch className="w-4 h-4" />
                    Azure Repos
                  </div>
                </SelectItem>
                <SelectItem value="bitbucket">
                  <div className="flex items-center gap-2">
                    <FolderGit2 className="w-4 h-4" />
                    Bitbucket
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {data.scmProvider && (
            <>
              <div>
                <Label htmlFor="repo-url">Repository URL</Label>
                <Input
                  id="repo-url"
                  placeholder="https://github.com/org/repo"
                  value={data.scmRepo || ""}
                  onChange={(e) => updateData({ scmRepo: e.target.value })}
                  className="mt-2"
                />
              </div>
              <Button variant="outline" className="w-full">
                <Github className="w-4 h-4 mr-2" />
                Connect to {data.scmProvider}
              </Button>
            </>
          )}
        </div>
      )}
    </div>
  );
};
