"use client";

import { Badge } from "@/components/ui/badge";
import { getVerdictBadgeVariant, type VerdictOrNull } from "@/lib/verdict";
import { AlertCircle, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { ClaimsTable } from "./claims-table";

interface FactCheckDisplayProps {
  factCheck: {
    fact_checker: {
      slug: string;
      name: string;
      version: string;
    };
    status: "pending" | "processing" | "completed" | "failed";
    verdict?: VerdictOrNull;
    confidence?: number | null;
    body?: string | null;
    claims?: Array<{
      claim: string;
      accuracy: string;
      reason: string;
    }> | null;
    error_message?: string | null;
    result?: {
      text: string;
      sources?: Array<{
        description: string;
        relevance?: string;
      }>;
    } | null;
    created_at: string;
    updated_at: string;
  };
}

export function FactCheckDisplay({ factCheck }: FactCheckDisplayProps) {
  return (
    <div className="space-y-4">
      {/* Fact Checker Info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold">{factCheck.fact_checker.name}</h3>
          <Badge variant="outline" className="text-xs">
            v{factCheck.fact_checker.version}
          </Badge>
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-2">
          {factCheck.status === "completed" && (
            <Badge variant="default">Completed</Badge>
          )}
          {factCheck.status === "processing" && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              Processing
            </Badge>
          )}
          {factCheck.status === "failed" && (
            <Badge variant="destructive">Failed</Badge>
          )}
          {factCheck.status === "pending" && (
            <Badge variant="outline">Pending</Badge>
          )}
        </div>
      </div>

      {/* Verdict and Confidence */}
      {factCheck.verdict && (
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Verdict:</span>
            <Badge variant={getVerdictBadgeVariant(factCheck.verdict)}>
              {factCheck.verdict}
            </Badge>
          </div>
          {factCheck.confidence !== null && factCheck.confidence !== undefined && (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Confidence:</span>
              <span className="text-sm">
                {(factCheck.confidence * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      )}

      {/* Error Message */}
      {factCheck.status === "failed" && factCheck.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-900">Error</p>
              <p className="text-sm text-red-700 mt-1">
                {factCheck.error_message}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Claims Table - Display above the fact check body */}
      {factCheck.status === "completed" && factCheck.claims && factCheck.claims.length > 0 && (
        <ClaimsTable claims={factCheck.claims} />
      )}

      {/* Fact Check Content - Use body field with proper markdown rendering */}
      {factCheck.status === "completed" && factCheck.body && (
        <div className="prose prose-sm max-w-none bg-gray-50 rounded-lg p-4 [&>h1]:font-bold [&>h1]:text-lg [&>h1]:mt-4 [&>h1]:mb-2 [&>h2]:font-bold [&>h2]:text-lg [&>h2]:mt-4 [&>h2]:mb-2 [&>h3]:font-semibold [&>h3]:text-base [&>h3]:mt-3 [&>h3]:mb-1 [&>p]:my-2 [&>ul]:my-2 [&>ul]:list-disc [&>ul]:pl-6 [&>ul>li]:my-1 [&>ol]:list-decimal [&>ol]:pl-6 [&>ol>li]:my-1 [&_a]:text-blue-600 [&_a]:underline [&_a:hover]:text-blue-800">
          <ReactMarkdown>{factCheck.body}</ReactMarkdown>
        </div>
      )}

      {/* Sources if available */}
      {factCheck.result?.sources && factCheck.result.sources.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-sm">Sources</h4>
          {factCheck.result.sources.map((source, idx) => (
            <div key={idx} className="bg-gray-50 rounded p-2 text-sm">
              <p>{source.description}</p>
              {source.relevance && (
                <p className="text-gray-600 text-xs mt-1">{source.relevance}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Timestamps */}
      <div className="text-xs text-gray-500 pt-2 border-t">
        <p>Created: {new Date(factCheck.created_at).toLocaleString()}</p>
        {factCheck.updated_at !== factCheck.created_at && (
          <p>Updated: {new Date(factCheck.updated_at).toLocaleString()}</p>
        )}
      </div>
    </div>
  );
}