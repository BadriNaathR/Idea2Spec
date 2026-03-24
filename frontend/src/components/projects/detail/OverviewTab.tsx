import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Clock, FileCode, Database, XCircle, Loader2, Upload, Plus, X, File as FileIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Project, api } from "@/lib/api";
import { useRef, useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

interface OverviewTabProps {
  project: Project;
  onProjectUpdate?: () => void;
}

// Common code file extensions
const CODE_FILE_EXTENSIONS = ".py,.js,.ts,.tsx,.jsx,.java,.cs,.cpp,.c,.h,.hpp,.go,.rb,.php,.swift,.kt,.scala,.rs,.sql,.json,.xml,.yaml,.yml,.md,.txt,.html,.css,.scss,.sass,.less,.vue,.svelte,.sh,.bash,.ps1,.bat,.dockerfile";

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

export const OverviewTab = ({ project, onProjectUpdate }: OverviewTabProps) => {
  const [isUploading, setIsUploading] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const getStatusIcon = () => {
    switch (project.status) {
      case 'ready':
        return <CheckCircle2 className="w-5 h-5 text-success" />;
      case 'processing':
        return <Loader2 className="w-5 h-5 text-primary animate-spin" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-destructive" />;
      default:
        return <Clock className="w-5 h-5 text-muted-foreground" />;
    }
  };

  const getStatusColor = () => {
    switch (project.status) {
      case 'ready':
        return 'bg-success/10 text-success';
      case 'processing':
        return 'bg-primary/10 text-primary';
      case 'failed':
        return 'bg-destructive/10 text-destructive';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  const getProgress = () => {
    switch (project.status) {
      case 'ready':
        return 100;
      case 'processing':
        return 50;
      case 'failed':
        return 0;
      default:
        return 10;
    }
  };

  const handleAddFiles = () => {
    setShowUploadDialog(true);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const newFiles = Array.from(files);
    const existingNames = new Set(selectedFiles.map(f => f.name));
    const uniqueNewFiles = newFiles.filter(f => !existingNames.has(f.name));
    setSelectedFiles(prev => [...prev, ...uniqueNewFiles]);
    
    // Reset input
    e.target.value = '';
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => {
      const newFiles = [...prev];
      newFiles.splice(index, 1);
      return newFiles;
    });
  };

  const handleUploadFiles = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    try {
      await api.addFilesToProject(project.id, selectedFiles);
      
      toast({
        title: "Files Added",
        description: `${selectedFiles.length} file(s) are being processed and added to the knowledge base.`,
      });
      
      setShowUploadDialog(false);
      setSelectedFiles([]);
      
      // Refresh project data
      if (onProjectUpdate) {
        onProjectUpdate();
      }
    } catch (error) {
      console.error('Error adding files:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to add files",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      const fileArray = Array.from(files);
      await api.addFilesToProject(project.id, fileArray);
      
      toast({
        title: "Files Added",
        description: `${fileArray.length} file(s) are being processed and added to the knowledge base.`,
      });
      
      // Refresh project data
      if (onProjectUpdate) {
        onProjectUpdate();
      }
    } catch (error) {
      console.error('Error adding files:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to add files",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
      // Reset input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Hidden file input for quick upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        multiple
        className="hidden"
        accept={CODE_FILE_EXTENSIONS}
      />

      {/* Upload Files Dialog */}
      <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Add Files to Project</DialogTitle>
            <DialogDescription>
              Select code files to add to the project's knowledge base. These will be analyzed and indexed.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="p-4 border-2 border-dashed rounded-lg hover:border-primary transition-colors">
              <Input
                type="file"
                multiple
                accept={CODE_FILE_EXTENSIONS}
                onChange={handleFileSelect}
                className="cursor-pointer"
              />
              <p className="text-xs text-muted-foreground mt-2">
                Supported: .py, .js, .ts, .java, .cs, .sql, .json, .xml, .yaml, .md, etc.
              </p>
            </div>
            
            {selectedFiles.length > 0 && (
              <div className="border rounded-lg">
                <div className="flex items-center justify-between p-2 border-b bg-muted/50">
                  <span className="text-sm font-medium">
                    {selectedFiles.length} file(s) selected
                  </span>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => setSelectedFiles([])}
                    className="text-destructive hover:text-destructive h-7 text-xs"
                  >
                    Clear All
                  </Button>
                </div>
                <ScrollArea className="max-h-[200px]">
                  <div className="p-2 space-y-1">
                    {selectedFiles.map((file, idx) => {
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
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleUploadFiles} 
              disabled={selectedFiles.length === 0 || isUploading}
              className="gradient-primary"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Add {selectedFiles.length} File(s)
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Project Info Card */}
      <Card className="p-6 shadow-medium">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Project Information</h3>
          <Button 
            onClick={handleAddFiles} 
            variant="outline" 
            size="sm"
            disabled={isUploading || project.status === 'processing'}
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-2" />
                Add Files
              </>
            )}
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Status</p>
            <div className="flex items-center gap-2">
              {getStatusIcon()}
              <Badge className={getStatusColor()}>
                {project.status.toUpperCase()}
              </Badge>
            </div>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Files Processed</p>
            <p className="text-lg font-semibold">{project.file_count}</p>
          </div>
          {project.domain && (
            <div>
              <p className="text-sm text-muted-foreground mb-1">Domain</p>
              <p className="text-lg font-semibold">{project.domain}</p>
            </div>
          )}
          {project.environment && (
            <div>
              <p className="text-sm text-muted-foreground mb-1">Environment</p>
              <p className="text-lg font-semibold">{project.environment}</p>
            </div>
          )}
          {project.source_type && (
            <div>
              <p className="text-sm text-muted-foreground mb-1">Source Type</p>
              <p className="text-lg font-semibold">{project.source_type.toUpperCase()}</p>
            </div>
          )}
          {project.scm_repo && (
            <div>
              <p className="text-sm text-muted-foreground mb-1">Repository</p>
              <p className="text-lg font-semibold truncate">{project.scm_repo}</p>
            </div>
          )}
        </div>
        {project.tags && project.tags.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-muted-foreground mb-2">Tags</p>
            <div className="flex flex-wrap gap-2">
              {project.tags.map((tag, idx) => (
                <Badge key={idx} variant="outline">{tag}</Badge>
              ))}
            </div>
          </div>
        )}
      </Card>

      <Card className="p-6 shadow-medium">
        <h3 className="text-lg font-semibold mb-4">Processing Status</h3>
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">Overall Completion</span>
              <span className="text-sm text-muted-foreground">{getProgress()}%</span>
            </div>
            <Progress value={getProgress()} className="h-3" />
          </div>
        </div>
      </Card>

      <Card className="p-6 shadow-medium">
        <h3 className="text-lg font-semibold mb-4">Timeline</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Created</span>
            <span className="font-medium">{new Date(project.created_at).toLocaleString()}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Last Updated</span>
            <span className="font-medium">{new Date(project.updated_at).toLocaleString()}</span>
          </div>
        </div>
      </Card>
    </div>
  );
};
