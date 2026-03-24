import { useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Code, Database, Layers, Image, Figma, Loader2, FileCode, Copy, Check } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api, ChatMessage as ApiChatMessage } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import ReactMarkdown from "react-markdown";

interface ChatTabProps {
  projectId: string;
}

type ChatMode = "code" | "db" | "system";

interface ChatMessageWithSources {
  role: string;
  content: string;
  sources?: Array<{ file_path: string; language?: string; score?: number }>;
}

export const ChatTab = ({ projectId }: ChatTabProps) => {
  const [mode, setMode] = useState<ChatMode>("system");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessageWithSources[]>([
    {
      role: "assistant",
      content: getModeWelcomeMessage("system"),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Update welcome message when mode changes
  useEffect(() => {
    if (messages.length === 1 && messages[0].role === "assistant") {
      setMessages([{ role: "assistant", content: getModeWelcomeMessage(mode) }]);
    }
  }, [mode]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    // Small delay to ensure DOM is updated
    const timer = setTimeout(() => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
      }
    }, 100);
    return () => clearTimeout(timer);
  }, [messages, isLoading]);

  function getModeWelcomeMessage(m: ChatMode): string {
    switch (m) {
      case "code":
        return "👋 **Hello! I'm your Software Architect assistant.**\n\nI can help you understand:\n- Code architecture and design patterns\n- Class relationships and dependencies\n- SOLID principles and code quality\n- Refactoring opportunities\n\nAsk me anything about your codebase!";
      case "db":
        return "👋 **Hello! I'm your Database Architect assistant.**\n\nI can help you with:\n- Schema analysis and normalization\n- Query optimization strategies\n- Index recommendations\n- Data modeling best practices\n\nAsk me anything about your database!";
      case "system":
        return "👋 **Hello! I'm your Technical Analyst assistant.**\n\nI explain your system in **plain English** - no jargon!\n\nI can help you understand:\n- How different parts of your app work together\n- What specific features do and why\n- The business logic behind the code\n\nI always cite my sources so you know where the information comes from. Ask away!";
      default:
        return "Hello! How can I help you today?";
    }
  }

  const copyToClipboard = async (text: string, index: number) => {
    await navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  useEffect(() => {
    loadChatHistory();
  }, [projectId]);

  const loadChatHistory = async () => {
    try {
      const history = await api.getChatHistory(projectId, 20);
      if (history.length > 0) {
        setMessages(history.map(msg => ({
          role: msg.role,
          content: msg.content
        })));
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  };

  const handleSend = async () => {
    if (!message.trim() || isLoading) return;
    
    const userMessage = message;
    setMessage("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);
    
    try {
      const response = await api.sendChatMessage(projectId, userMessage, mode);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: response.response,
        sources: response.sources
      }]);
    } catch (error) {
      console.error('Error sending message:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to send message",
        variant: "destructive",
      });
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again."
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const getModeIcon = (m: ChatMode) => {
    switch (m) {
      case "code":
        return Code;
      case "db":
        return Database;
      case "system":
        return Layers;
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <Card className="lg:col-span-2 p-6 shadow-medium flex flex-col" style={{ height: "600px" }}>
        <div className="mb-4">
          <Tabs value={mode} onValueChange={(v) => setMode(v as ChatMode)}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="code" className="flex items-center gap-2">
                <Code className="w-4 h-4" />
                Code
              </TabsTrigger>
              <TabsTrigger value="db" className="flex items-center gap-2">
                <Database className="w-4 h-4" />
                Database
              </TabsTrigger>
              <TabsTrigger value="system" className="flex items-center gap-2">
                <Layers className="w-4 h-4" />
                Full System
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <ScrollArea className="flex-1 pr-4 mb-4">
          <div className="flex flex-col space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-lg p-4 ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  {msg.role === "user" ? (
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  ) : (
                    <div className="relative">
                      {/* Copy button for assistant messages */}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="absolute top-0 right-0 h-6 w-6 p-0 opacity-50 hover:opacity-100"
                        onClick={() => copyToClipboard(msg.content, idx)}
                      >
                        {copiedIndex === idx ? (
                          <Check className="h-3 w-3 text-green-500" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </Button>
                      {/* Markdown rendered content */}
                      <div className="prose prose-sm dark:prose-invert max-w-none pr-8
                        prose-headings:mt-3 prose-headings:mb-2 prose-headings:font-semibold
                        prose-h2:text-base prose-h3:text-sm
                        prose-p:my-1.5 prose-p:leading-relaxed
                        prose-ul:my-1.5 prose-ol:my-1.5
                        prose-li:my-0.5
                        prose-code:bg-slate-800 prose-code:text-slate-200 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs
                        prose-pre:bg-slate-900 prose-pre:p-3 prose-pre:rounded-lg prose-pre:my-2
                        prose-strong:font-semibold
                        prose-a:text-blue-500 prose-a:no-underline hover:prose-a:underline
                      ">
                        <ReactMarkdown
                          components={{
                            // Custom code block rendering
                            code({ node, className, children, ...props }) {
                              const match = /language-(\w+)/.exec(className || '');
                              const isInline = !match && !className;
                              return isInline ? (
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              ) : (
                                <div className="relative group">
                                  {match && (
                                    <span className="absolute top-2 right-2 text-xs text-slate-500 font-mono">
                                      {match[1]}
                                    </span>
                                  )}
                                  <code className={className} {...props}>
                                    {children}
                                  </code>
                                </div>
                              );
                            },
                            // Make links open in new tab
                            a({ node, children, ...props }) {
                              return (
                                <a target="_blank" rel="noopener noreferrer" {...props}>
                                  {children}
                                </a>
                              );
                            }
                          }}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                      {/* Sources section for assistant messages */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-border/50">
                          <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1.5">
                            <FileCode className="h-3 w-3" />
                            <span className="font-medium">Referenced Files:</span>
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.sources.map((source, sIdx) => (
                              <span
                                key={sIdx}
                                className="inline-flex items-center gap-1 px-2 py-0.5 bg-background rounded text-xs font-mono text-muted-foreground border"
                                title={`Relevance: ${Math.round((source.score || 0) * 100)}%`}
                              >
                                {source.file_path.split('/').pop()}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg p-4">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Analyzing...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        <div className="flex gap-2">
          <Textarea
            placeholder={`Ask about your ${mode === "code" ? "code" : mode === "db" ? "database" : "application"}...`}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            className="min-h-[60px] resize-none"
          />
          <Button onClick={handleSend} className="gradient-primary text-primary-foreground" disabled={isLoading}>
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
      </Card>

      <div className="space-y-4">
        <Card className="p-6 shadow-medium">
          <h3 className="font-semibold mb-4">Quick Actions</h3>
          <div className="space-y-2">
            <Button variant="outline" className="w-full justify-start">
              <Image className="w-4 h-4 mr-2" />
              Generate Diagram
            </Button>
            <Button variant="outline" className="w-full justify-start">
              <Figma className="w-4 h-4 mr-2" />
              Generate Wireframe
            </Button>
          </div>
        </Card>

        <Card className="p-6 shadow-medium">
          <h3 className="font-semibold mb-4">Mode Info</h3>
          {mode === "code" && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400">
                <Code className="w-4 h-4" />
                Software Architect
              </div>
              <p className="text-sm text-muted-foreground">
                Technical, architect-level analysis of code structure, design patterns, 
                SOLID principles, and refactoring recommendations.
              </p>
            </div>
          )}
          {mode === "db" && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-green-600 dark:text-green-400">
                <Database className="w-4 h-4" />
                Database Architect
              </div>
              <p className="text-sm text-muted-foreground">
                DBA-level analysis of schemas, normalization, query optimization, 
                indexing strategies, and data modeling best practices.
              </p>
            </div>
          )}
          {mode === "system" && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-medium text-purple-600 dark:text-purple-400">
                <Layers className="w-4 h-4" />
                Technical Analyst
              </div>
              <p className="text-sm text-muted-foreground">
                Plain English explanations of how your system works. 
                Bridges technical and business understanding with cited sources.
              </p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
