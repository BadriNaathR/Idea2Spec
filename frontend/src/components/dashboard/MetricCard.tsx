import { Card } from "@/components/ui/card";
import { LucideIcon, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string;
  change: string;
  icon: LucideIcon;
  trend: "up" | "down" | "neutral";
  iconColor?: "cyan" | "blue" | "purple" | "green";
}

export const MetricCard = ({ 
  title, 
  value, 
  change, 
  icon: Icon, 
  trend,
  iconColor = "cyan"
}: MetricCardProps) => {
  const trendIcon = {
    up: TrendingUp,
    down: TrendingDown,
    neutral: Minus,
  }[trend];
  
  const TrendIcon = trendIcon;
  
  const trendColor = {
    up: "text-emerald-500",
    down: "text-red-500",
    neutral: "text-gray-400",
  }[trend];

  const iconColorClasses = {
    cyan: "bg-cyan-100 text-cyan-600",
    blue: "bg-blue-100 text-blue-600",
    purple: "bg-purple-100 text-purple-600",
    green: "bg-emerald-100 text-emerald-600",
  }[iconColor];

  const changeColor = {
    up: "text-emerald-500",
    down: "text-red-500",
    neutral: "text-gray-500",
  }[trend];

  return (
    <Card className="p-6 bg-white rounded-2xl shadow-sm hover:shadow-md transition-all duration-200 border border-gray-200">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${iconColorClasses}`}>
          <Icon className="w-6 h-6" />
        </div>
        <TrendIcon className={`w-5 h-5 ${trendColor}`} />
      </div>
      <p className="text-sm font-medium text-gray-500 mb-2">{title}</p>
      <p className="text-3xl font-bold text-gray-900 mb-1">{value}</p>
      <p className={`text-sm ${changeColor}`}>{change}</p>
    </Card>
  );
};
