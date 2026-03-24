import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface BasicInfoStepProps {
  data: any;
  updateData: (data: any) => void;
}

export const BasicInfoStep = ({ data, updateData }: BasicInfoStepProps) => {
  const [tagInput, setTagInput] = useState("");

  const handleAddTag = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && tagInput.trim()) {
      e.preventDefault();
      updateData({ tags: [...(data.tags || []), tagInput.trim()] });
      setTagInput("");
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    updateData({ tags: data.tags.filter((tag: string) => tag !== tagToRemove) });
  };

  return (
    <div className="space-y-6">
      <div>
        <Label htmlFor="name">Application Name *</Label>
        <Input
          id="name"
          placeholder="e.g., Legacy Banking System"
          value={data.name || ""}
          onChange={(e) => updateData({ name: e.target.value })}
          className="mt-2"
        />
      </div>

      <div>
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          placeholder="Describe the application, its purpose, and key functionality..."
          value={data.description || ""}
          onChange={(e) => updateData({ description: e.target.value })}
          className="mt-2 min-h-24"
        />
      </div>

      <div>
        <Label htmlFor="domain">Business Domain</Label>
        <Select
          value={data.domain || ""}
          onValueChange={(value) => updateData({ domain: value })}
        >
          <SelectTrigger className="mt-2">
            <SelectValue placeholder="Select domain" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="banking">Banking & Finance</SelectItem>
            <SelectItem value="healthcare">Healthcare</SelectItem>
            <SelectItem value="retail">Retail & E-commerce</SelectItem>
            <SelectItem value="manufacturing">Manufacturing</SelectItem>
            <SelectItem value="insurance">Insurance</SelectItem>
            <SelectItem value="telecom">Telecommunications</SelectItem>
            <SelectItem value="AI_for_IT">AI for IT</SelectItem>
            <SelectItem value="other">Other</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="environment">Environment Type</Label>
        <Select
          value={data.environment || ""}
          onValueChange={(value) => updateData({ environment: value })}
        >
          <SelectTrigger className="mt-2">
            <SelectValue placeholder="Select environment" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="legacy">Legacy System</SelectItem>
            <SelectItem value="migration">Migration Target</SelectItem>
            <SelectItem value="hybrid">Hybrid Environment</SelectItem>
            <SelectItem value="brownfield">Brown Field Project</SelectItem>
            <SelectItem value="greenfield">Greenfield Project</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="tags">Tags</Label>
        <Input
          id="tags"
          placeholder="Type a tag and press Enter"
          value={tagInput}
          onChange={(e) => setTagInput(e.target.value)}
          onKeyDown={handleAddTag}
          className="mt-2"
        />
        {data.tags && data.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {data.tags.map((tag: string) => (
              <Badge key={tag} variant="secondary" className="pl-3 pr-1">
                {tag}
                <button
                  onClick={() => handleRemoveTag(tag)}
                  className="ml-2 hover:bg-muted rounded-full p-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
