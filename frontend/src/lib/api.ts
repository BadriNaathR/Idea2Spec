/**
 * AppRelic API Client
 * Connects frontend to FastAPI backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// ==================== TYPES ====================

export interface Project {
  id: string;
  name: string;
  description?: string;
  domain?: string;
  tags?: string[];
  environment?: string;
  source_type?: string;
  scm_provider?: string;
  scm_repo?: string;
  scm_branch?: string;
  status: string;
  file_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  mode: 'code' | 'db' | 'system';
  metadata?: any;
  created_at: string;
}

export interface ChatResponse {
  response: string;
  sources: Array<{
    file_path: string;
    content: string;
    score: number;
  }>;
  suggestions?: string[];
  mode: string;
}

export interface Analysis {
  analysis_id: string;
  project_id: string;
  analysis_type: string;
  model: string;
  status: 'pending' | 'in-progress' | 'complete' | 'partial' | 'failed';
  result?: any;
  token_count?: number;
  cost?: number;
  quality_score?: number;
  error_message?: string;
  created_at: string;
}

export interface Insights {
  code_hotspots: Array<{
    file_path: string;
    complexity: number;
    issues: string[];
    recommendation: string;
  }>;
  db_optimizations: Array<{
    query: string;
    issue: string;
    recommendation: string;
    impact: string;
  }>;
  modernization_recommendations: Array<{
    category: string;
    current: string;
    recommended: string;
    effort: string;
    priority: string;
  }>;
  tech_stack_analysis: {
    languages: Record<string, number>;
    frameworks: string[];
    dependencies: string[];
    risks: string[];
  };
}

export interface AnalysisProgress {
  analysis_id: string;
  status: string;
  current_step: number;
  total_steps: number;
  current_section: string;
  completed_sections: string[];
  percent_complete: number;
  message: string;
  eta_seconds?: number | null;  // Estimated time remaining in seconds
}

export interface DashboardStats {
  projects: {
    total: number;
    this_month: number;
  };
  deliverables: {
    total: number;
    today: number;
    this_week: number;
  };
  tokens: {
    total: number;
    today: number;
  };
  cost: {
    total: number;
    today: number;
  };
}

export interface RecentActivityItem {
  id: string;
  type: 'deliverable' | 'project' | 'warning' | 'error' | 'processing' | 'pending';
  title: string;
  project: string;
  project_id: string;
  timestamp: string | null;
  status: string;
  analysis_type: string | null;
}

export interface SupportingDoc {
  file: File;
  type: string;
  priority: string;
}

export interface ProjectCreateData {
  name: string;
  description?: string;
  domain?: string;
  tags?: string;
  environment?: string;
  source_type: 'files' | 'zip' | 'github' | 'scm';
  scm_provider?: string;
  scm_repo?: string;
  scm_branch?: string;
  scm_token?: string;
  files?: File[];
  indexing_mode?: 'initial' | 'append';  // initial = fresh index, append = add to existing
  include_db_introspection?: boolean;
  include_ui_parsing?: boolean;
  supporting_docs?: SupportingDoc[];
  ad_hoc_content?: string;
}

// ==================== API CLIENT ====================

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // ==================== PROJECT ENDPOINTS ====================

  async createProject(data: ProjectCreateData): Promise<Project> {
    const formData = new FormData();
    formData.append('name', data.name);
    if (data.description) formData.append('description', data.description);
    if (data.domain) formData.append('domain', data.domain);
    if (data.tags) formData.append('tags', data.tags);
    if (data.environment) formData.append('environment', data.environment);
    // Map 'scm' to 'github' for backend compatibility
    const sourceType = data.source_type === 'scm' ? 'github' : data.source_type;
    formData.append('source_type', sourceType);
    if (data.scm_provider) formData.append('scm_provider', data.scm_provider);
    if (data.scm_repo) formData.append('scm_repo', data.scm_repo);
    if (data.scm_branch) formData.append('scm_branch', data.scm_branch);
    if (data.scm_token) formData.append('scm_token', data.scm_token);
    if (data.indexing_mode) formData.append('indexing_mode', data.indexing_mode);
    if (data.include_db_introspection !== undefined) formData.append('include_db_introspection', data.include_db_introspection.toString());
    if (data.include_ui_parsing !== undefined) formData.append('include_ui_parsing', data.include_ui_parsing.toString());
    if (data.ad_hoc_content) formData.append('ad_hoc_content', data.ad_hoc_content);
    
    if (data.files) {
      data.files.forEach((file) => {
        formData.append('files', file);
      });
    }

    // Add supporting documents with metadata
    if (data.supporting_docs) {
      data.supporting_docs.forEach((doc, index) => {
        formData.append('supporting_files', doc.file);
        formData.append('supporting_types', doc.type);
        formData.append('supporting_priorities', doc.priority);
      });
    }

    return this.request<Project>('/projects', {
      method: 'POST',
      body: formData,
    });
  }

  async listProjects(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<Project[]> {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.status) queryParams.append('status', params.status);

    const query = queryParams.toString();
    return this.request<Project[]>(`/projects${query ? `?${query}` : ''}`);
  }

  async getProject(projectId: string): Promise<Project> {
    return this.request<Project>(`/projects/${projectId}`);
  }

  async deleteProject(projectId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/projects/${projectId}`, {
      method: 'DELETE',
    });
  }

  async addFilesToProject(
    projectId: string, 
    files: File[],
    options?: {
      supportingDocs?: SupportingDoc[];
      adHocContent?: string;
    }
  ): Promise<{ message: string; project_id: string; files_count: number }> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    // Add supporting documents if provided
    if (options?.supportingDocs) {
      options.supportingDocs.forEach((doc) => {
        formData.append('supporting_files', doc.file);
        formData.append('supporting_types', doc.type);
        formData.append('supporting_priorities', doc.priority);
      });
    }

    // Add ad-hoc content if provided
    if (options?.adHocContent) {
      formData.append('ad_hoc_content', options.adHocContent);
    }

    return this.request<{ message: string; project_id: string; files_count: number }>(
      `/projects/${projectId}/files`,
      {
        method: 'POST',
        body: formData,
      }
    );
  }

  // ==================== CHAT ENDPOINTS ====================

  async sendChatMessage(
    projectId: string,
    message: string,
    mode: 'code' | 'db' | 'system' = 'system',
    context?: any
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        project_id: projectId,
        message,
        mode,
        context,
      }),
    });
  }

  async getChatHistory(
    projectId: string,
    limit: number = 50
  ): Promise<ChatMessage[]> {
    return this.request<ChatMessage[]>(
      `/projects/${projectId}/chat-history?limit=${limit}`
    );
  }

  // ==================== ANALYSIS ENDPOINTS ====================

  async runAnalysis(
    projectId: string,
    analysisType: string,
    model: string = 'azure/genailab-maas-gpt-4.1-mini',
    options?: any
  ): Promise<Analysis> {
    return this.request<Analysis>('/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        project_id: projectId,
        analysis_type: analysisType,
        model,
        options,
      }),
    });
  }

  async listAnalyses(
    projectId: string,
    analysisType?: string
  ): Promise<Analysis[]> {
    const query = analysisType ? `?analysis_type=${analysisType}` : '';
    return this.request<Analysis[]>(`/projects/${projectId}/analyses${query}`);
  }

  async getAnalysis(analysisId: string): Promise<Analysis> {
    return this.request<Analysis>(`/analyses/${analysisId}`);
  }

  async reviewUserStories(analysisId: string): Promise<{
    confidence_score: number;
    rationale: string;
    strengths: string[];
    gaps: string[];
    reviewer_model?: string;
    error?: boolean;
  }> {
    return this.request(`/analyses/${analysisId}/review`, { method: 'POST' });
  }

  async regenerateAnalysis(
    analysisId: string,
    model: string = 'azure/genailab-maas-gpt-4.1-mini',
    feedback?: string
  ): Promise<Analysis> {
    const params = new URLSearchParams({ model });
    if (feedback) params.append('feedback', feedback);
    return this.request<Analysis>(
      `/analyses/${analysisId}/regenerate?${params.toString()}`,
      { method: 'POST' }
    );
  }

  async getAnalysisProgress(analysisId: string): Promise<AnalysisProgress> {
    return this.request<AnalysisProgress>(`/analyses/${analysisId}/progress`);
  }

  async downloadAnalysis(
    analysisId: string,
    format: 'word' | 'markdown' | 'html' = 'word'
  ): Promise<Blob> {
    const url = `${this.baseUrl}/analyses/${analysisId}/download?format=${format}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }
    
    return response.blob();
  }

  // ==================== INSIGHTS ENDPOINTS ====================

  async getInsights(projectId: string): Promise<Insights> {
    return this.request<Insights>(`/projects/${projectId}/insights`);
  }

  // ==================== DIAGRAM ENDPOINTS ====================

  async generateArchitectureDiagram(projectId: string): Promise<{
    diagram_type: string;
    format: string;
    diagram: string;
    preview_url?: string;
  }> {
    return this.request(`/projects/${projectId}/diagrams/architecture`, {
      method: 'POST',
    });
  }

  async generateDatabaseDiagram(projectId: string): Promise<{
    diagram_type: string;
    format: string;
    diagram: string;
    preview_url?: string;
  }> {
    return this.request(`/projects/${projectId}/diagrams/database`, {
      method: 'POST',
    });
  }

  // ==================== AUTH ====================

  async login(username: string, password: string): Promise<{ id: string; username: string; role: 'business_analyst' | 'reviewer'; full_name: string }> {
    // Use absolute URL to bypass any proxy/base URL issues
    const url = `${window.location.origin}/api/auth/login`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return response.json();
  }

  // ==================== REVIEW ====================

  async submitForReview(analysisId: string, projectId: string, submittedBy: string, checklist: string[] = []): Promise<any> {
    return this.request('/reviews/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analysis_id: analysisId, project_id: projectId, submitted_by: submittedBy, checklist }),
    });
  }

  async getPendingReviews(): Promise<any[]> {
    return this.request('/reviews/pending');
  }

  async getReviewByAnalysis(analysisId: string): Promise<any | null> {
    return this.request(`/reviews/analysis/${analysisId}`);
  }

  async humanReviewDecision(reviewId: string, reviewerId: string, decision: 'sign_off' | 'return_to_ba', humanComments?: string, aiOverrides?: Record<string, any>): Promise<any> {
    return this.request(`/reviews/${reviewId}/human-decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer_id: reviewerId, decision, human_comments: humanComments, ai_overrides: aiOverrides || {} }),
    });
  }

  // ==================== HEALTH CHECK ====================

  async healthCheck(): Promise<{
    status: string;
    timestamp: string;
    services: Record<string, string>;
  }> {
    return this.request('/health');
  }

  // ==================== STATS ENDPOINT ====================

  async getStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>('/stats');
  }

  // ==================== RECENT ACTIVITY ENDPOINT ====================

  async getRecentActivity(limit: number = 10): Promise<RecentActivityItem[]> {
    return this.request<RecentActivityItem[]>(`/recent-activity?limit=${limit}`);
  }
}

// ==================== SINGLETON EXPORT ====================

export const api = new ApiClient(API_BASE_URL);

// ==================== HELPER FUNCTIONS ====================

export const downloadFile = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};
