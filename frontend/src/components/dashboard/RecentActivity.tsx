import { Card } from "@/components/ui/card";
import { FileText, Database, Code, Clock, FolderPlus, AlertTriangle, XCircle, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { api, RecentActivityItem } from "@/lib/api";
import { useNavigate } from "react-router-dom";

// Format relative time (e.g., "2 hours ago")
const formatRelativeTime = (timestamp: string | null): string => {
  if (!timestamp) return "Unknown";
  
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffSeconds < 60) return "Just now";
  if (diffMinutes < 60) return `${diffMinutes} min${diffMinutes > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  
  return date.toLocaleDateString();
};

// Get icon based on activity type
const getActivityIcon = (type: string, analysisType: string | null) => {
  if (type === 'project') return FolderPlus;
  if (type === 'error') return XCircle;
  if (type === 'warning') return AlertTriangle;
  if (type === 'processing') return Loader2;
  
  // For deliverables, use specific icons based on analysis type
  if (analysisType === 'data_dictionary' || analysisType === 'api_spec') return Database;
  if (analysisType === 'test_cases' || analysisType === 'sdd') return Code;
  
  return FileText;
};

// Get icon color based on activity type
const getIconColor = (type: string) => {
  switch (type) {
    case 'deliverable': return 'bg-green-100 text-green-600';
    case 'project': return 'bg-blue-100 text-blue-600';
    case 'warning': return 'bg-yellow-100 text-yellow-600';
    case 'error': return 'bg-red-100 text-red-600';
    case 'processing': return 'bg-purple-100 text-purple-600';
    case 'pending': return 'bg-gray-100 text-gray-600';
    default: return 'bg-accent/10 text-accent';
  }
};

export const RecentActivity = () => {
  const [activities, setActivities] = useState<RecentActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadActivities();
  }, []);

  const loadActivities = async () => {
    try {
      const data = await api.getRecentActivity(10);
      setActivities(data);
    } catch (error) {
      console.error('Error loading activities:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6 shadow-medium">
      <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
      
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      ) : activities.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground text-sm">
          No recent activity
        </div>
      ) : (
        <div className="space-y-4">
          {activities.slice(0, 5).map((activity) => {
            const Icon = getActivityIcon(activity.type, activity.analysis_type);
            const iconColor = getIconColor(activity.type);
            
            return (
              <div 
                key={activity.id} 
                className="flex items-start gap-3 cursor-pointer hover:bg-muted/50 rounded-lg p-2 -m-2 transition-colors"
                onClick={() => navigate(`/projects/${activity.project_id}`)}
              >
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${iconColor}`}>
                  <Icon className={`w-5 h-5 ${activity.type === 'processing' ? 'animate-spin' : ''}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm">{activity.title}</p>
                  <p className="text-xs text-muted-foreground truncate">{activity.project}</p>
                  <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    {formatRelativeTime(activity.timestamp)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
