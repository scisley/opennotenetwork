"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  CheckCircle,
  Circle,
  Loader2,
  Brain,
  Search,
  FileText,
  Link,
  Code,
} from "lucide-react";

interface NodeUpdate {
  node: string;
  data: any;
  timestamp: number;
}

interface FactCheckStreamProps {
  updates: NodeUpdate[];
  isProcessing?: boolean;
}

interface ContentItem {
  id?: string;
  type: string;
  text?: string;
  summary?: Array<{ text: string; type: string }>;
  action?: { type: string; query: string };
  status?: string;
  annotations?: Array<{
    url: string;
    type: string;
    title: string;
    start_index: number;
    end_index: number;
  }>;
}

// Format node name for display
function formatNodeName(nodeName: string): string {
  return nodeName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

// Get color for node based on hash of name
function getNodeColor(nodeName: string): string {
  const colors = [
    "border-blue-500 text-blue-700 bg-blue-50",
    "border-green-500 text-green-700 bg-green-50",
    "border-purple-500 text-purple-700 bg-purple-50",
    "border-orange-500 text-orange-700 bg-orange-50",
    "border-pink-500 text-pink-700 bg-pink-50",
    "border-indigo-500 text-indigo-700 bg-indigo-50",
  ];

  const hash = nodeName
    .split("")
    .reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

// Get icon for content type
function getContentIcon(type: string) {
  switch (type) {
    case "reasoning":
      return <Brain className="h-4 w-4" />;
    case "web_search_call":
      return <Search className="h-4 w-4" />;
    case "text":
      return <FileText className="h-4 w-4" />;
    case "url_citation":
      return <Link className="h-4 w-4" />;
    default:
      return <Circle className="h-4 w-4" />;
  }
}

// Extract content items from agent response structure
function extractAgentContent(data: any): ContentItem[] {
  if (!data || typeof data !== "object") return [];

  // Look for agent responses (advocate, adversary, etc.)
  const agentKeys = Object.keys(data).filter(
    (key) => typeof data[key] === "object" && data[key] !== null
  );

  for (const key of agentKeys) {
    const agentData = data[key];

    // Check for nested structure with kwargs.content
    if (agentData.kwargs?.content && Array.isArray(agentData.kwargs.content)) {
      return agentData.kwargs.content;
    }

    // Check for direct content array
    if (agentData.content && Array.isArray(agentData.content)) {
      return agentData.content;
    }
  }

  return [];
}

// Extract meaningful summary from node data
function extractNodeSummary(nodeName: string, data: any): string {
  // First try to extract from agent content
  const contentItems = extractAgentContent(data);
  if (contentItems.length > 0) {
    const summaryParts = [];

    // Count different types of content
    const reasoning = contentItems.filter((item) => item.type === "reasoning");
    const searches = contentItems.filter(
      (item) => item.type === "web_search_call"
    );
    const texts = contentItems.filter((item) => item.type === "text");

    if (reasoning.length > 0) {
      // Try to get reasoning summary
      const withSummary = reasoning.find(
        (r) => r.summary && r.summary.length > 0
      );
      if (withSummary && withSummary.summary?.[0]?.text) {
        const preview = withSummary.summary[0].text.substring(0, 100);
        return (
          preview + (withSummary.summary[0].text.length > 100 ? "..." : "")
        );
      }
      summaryParts.push(
        `${reasoning.length} reasoning step${reasoning.length !== 1 ? "s" : ""}`
      );
    }

    if (searches.length > 0) {
      summaryParts.push(
        `${searches.length} web search${searches.length !== 1 ? "es" : ""}`
      );
    }

    if (texts.length > 0) {
      // Count citations
      const citations = texts.reduce(
        (acc, item) => acc + (item.annotations?.length || 0),
        0
      );
      if (citations > 0) {
        summaryParts.push(`${citations} citation${citations !== 1 ? "s" : ""}`);
      }
    }

    if (summaryParts.length > 0) {
      return `Completed with ${summaryParts.join(", ")}`;
    }
  }

  // Fall back to existing logic
  if (!data || typeof data !== "object") {
    return "Processing complete";
  }

  // Look for common patterns in the data, regardless of node name

  // Pattern 1: Eligibility check (has is_eligible field)
  if ("is_eligible" in data) {
    const eligible = data.is_eligible;
    const reason = data.eligibility_reason || data.reason || "";
    return eligible
      ? `✓ Eligible${reason ? ": " + reason : ""}`
      : `✗ Not eligible${reason ? ": " + reason : ""}`;
  }

  // Pattern 2: Verdict/confidence (has verdict field)
  if ("verdict" in data && data.verdict) {
    const confidence = data.confidence;
    if (confidence !== undefined && confidence !== null) {
      return `Verdict: ${data.verdict} (${Math.round(
        confidence * 100
      )}% confidence)`;
    }
    return `Verdict: ${data.verdict}`;
  }

  // Pattern 3: Body text (has body field)
  if ("body" in data && typeof data.body === "string") {
    const preview = data.body.substring(0, 100);
    return preview + (data.body.length > 100 ? "..." : "");
  }

  // Pattern 4: Additional context (has additional_context field)
  if ("additional_context" in data) {
    return data.additional_context || "Context gathered";
  }

  // Pattern 5: Error or failure (has error or error_message field)
  if ("error" in data || "error_message" in data) {
    const error = data.error || data.error_message;
    return `⚠️ Error: ${error}`;
  }

  // Pattern 6: Status field
  if ("status" in data && typeof data.status === "string") {
    return `Status: ${data.status}`;
  }

  // Pattern 7: Result field with text
  if ("result" in data) {
    if (typeof data.result === "string") {
      const preview = data.result.substring(0, 100);
      return preview + (data.result.length > 100 ? "..." : "");
    }
    if (typeof data.result === "object" && data.result.text) {
      const preview = data.result.text.substring(0, 100);
      return preview + (data.result.text.length > 100 ? "..." : "");
    }
  }

  // Pattern 8: Generic completion indicators
  if ("complete" in data || "completed" in data || "done" in data) {
    return "Step completed";
  }

  // Pattern 9: Look for any string field that might be a message
  const messageFields = [
    "message",
    "text",
    "output",
    "response",
    "answer",
    "conclusion",
  ];
  for (const field of messageFields) {
    if (field in data && typeof data[field] === "string" && data[field]) {
      const preview = data[field].substring(0, 100);
      return preview + (data[field].length > 100 ? "..." : "");
    }
  }

  // Pattern 10: If there's any non-empty data, consider it complete
  const keys = Object.keys(data);
  if (keys.length > 0) {
    // Try to create a simple summary from the first few fields
    const summaryParts = [];
    for (let i = 0; i < Math.min(2, keys.length); i++) {
      const key = keys[i];
      const value = data[key];
      if (value === null || value === undefined) continue;

      if (typeof value === "boolean") {
        summaryParts.push(`${key}: ${value ? "Yes" : "No"}`);
      } else if (typeof value === "number") {
        summaryParts.push(`${key}: ${value}`);
      } else if (typeof value === "string" && value.length < 50) {
        summaryParts.push(`${key}: ${value}`);
      }
    }

    if (summaryParts.length > 0) {
      return summaryParts.join(", ");
    }

    return "Step completed";
  }

  return "Processing complete";
}

export function FactCheckStream({
  updates,
  isProcessing = false,
}: FactCheckStreamProps) {
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  const toggleExpanded = (node: string) => {
    setExpandedNodes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(node)) {
        newSet.delete(node);
      } else {
        newSet.add(node);
      }
      return newSet;
    });
  };

  // Group updates by node
  const nodeGroups = updates.reduce((acc, update) => {
    if (!acc[update.node]) {
      acc[update.node] = [];
    }
    acc[update.node].push(update);
    return acc;
  }, {} as Record<string, NodeUpdate[]>);

  return (
    <div className="space-y-3">
      {Object.entries(nodeGroups).map(([nodeName, nodeUpdates]) => {
        const isExpanded = expandedNodes.has(nodeName);
        const latestData = nodeUpdates[nodeUpdates.length - 1].data;

        return (
          <div
            key={nodeName}
            className={`border-l-4 rounded-lg p-4 transition-all ${getNodeColor(
              nodeName
            )}`}
          >
            <div
              className="flex items-start justify-between cursor-pointer"
              onClick={() => toggleExpanded(nodeName)}
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  <h3 className="font-semibold">{formatNodeName(nodeName)}</h3>
                </div>
                <p className="text-sm mt-1 opacity-90">
                  {extractNodeSummary(nodeName, latestData)}
                </p>
              </div>
              <button className="text-xs opacity-60 hover:opacity-100">
                {isExpanded ? "Hide" : "Show"} Details
              </button>
            </div>

            {isExpanded && (
              <div className="mt-3 space-y-3">
                {/* Show structured content if available */}
                {(() => {
                  const contentItems = extractAgentContent(latestData);
                  if (contentItems.length > 0) {
                    return (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium opacity-80">
                          Content Analysis:
                        </h4>
                        {contentItems.map((item, idx) => (
                          <div
                            key={idx}
                            className="bg-white/30 rounded p-3 text-sm"
                          >
                            <div className="flex items-start gap-2">
                              <div className="mt-0.5 opacity-70">
                                {getContentIcon(item.type)}
                              </div>
                              <div className="flex-1">
                                <div className="font-medium capitalize mb-1">
                                  {item.type.replace(/_/g, " ")}
                                </div>

                                {/* Reasoning summary */}
                                {item.type === "reasoning" &&
                                  item.summary &&
                                  item.summary.length > 0 && (
                                    <div className="text-xs opacity-80 prose prose-xs max-w-none">
                                      <ReactMarkdown>
                                        {item.summary[0].text}
                                      </ReactMarkdown>
                                    </div>
                                  )}

                                {/* Web search query */}
                                {item.type === "web_search_call" &&
                                  item.action && (
                                    <div className="text-xs">
                                      <span className="opacity-70">Query:</span>{" "}
                                      &quot;{item.action.query}&quot;
                                    </div>
                                  )}

                                {/* Text with citations */}
                                {item.type === "text" && (
                                  <div className="text-xs space-y-1">
                                    {item.text && (
                                      <div className="opacity-80 prose prose-xs max-w-none">
                                        <ReactMarkdown>
                                          {item.text}
                                        </ReactMarkdown>
                                      </div>
                                    )}
                                    {item.annotations &&
                                      item.annotations.length > 0 && (
                                        <div className="mt-2 space-y-1">
                                          <div className="font-medium">
                                            Citations:
                                          </div>
                                          {item.annotations.map(
                                            (ann, annIdx) => (
                                              <div
                                                key={annIdx}
                                                className="flex items-start gap-1 ml-2"
                                              >
                                                <Link className="h-3 w-3 mt-0.5 opacity-50" />
                                                <a
                                                  href={ann.url}
                                                  target="_blank"
                                                  rel="noopener noreferrer"
                                                  className="text-blue-600 hover:underline break-all"
                                                >
                                                  {ann.title ||
                                                    ann.url.substring(0, 50)}
                                                </a>
                                              </div>
                                            )
                                          )}
                                        </div>
                                      )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  }
                  return null;
                })()}

                {/* Raw JSON viewer */}
                <details className="group">
                  <summary className="cursor-pointer flex items-center gap-2 text-sm opacity-70 hover:opacity-100">
                    <Code className="h-4 w-4" />
                    <span>Show Raw Data</span>
                  </summary>
                  <div className="mt-2 pt-2 border-t border-current opacity-20">
                    <pre className="text-xs overflow-auto max-h-64 bg-white/50 rounded p-2">
                      {JSON.stringify(latestData, null, 2)}
                    </pre>
                  </div>
                </details>
              </div>
            )}
          </div>
        );
      })}

      {/* Show spinner at the bottom when processing */}
      {isProcessing && updates.length > 0 && (
        <div className="text-center py-4">
          <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-600">Processing...</p>
        </div>
      )}

      {/* Show initial loading message when no updates yet */}
      {updates.length === 0 && (
        <div className="text-center py-8">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600">Starting fact check...</p>
          <p className="text-sm text-gray-500 mt-2">
            This may take a few moments
          </p>
        </div>
      )}
    </div>
  );
}
