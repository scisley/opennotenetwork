"use client";

import { AlertCircle, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { ClaimsTable } from "./claims-table";

interface FactCheckDisplayPublicProps {
  factCheck: {
    fact_checker: {
      slug: string;
      name: string;
      version: string;
    };
    status: "pending" | "processing" | "completed" | "failed";
    verdict?: string | null;
    body?: string | null;
    claims?: Array<{
      claim: string;
      accuracy: string;
      reason: string;
    }> | null;
    error_message?: string | null;
    created_at: string;
    updated_at: string;
  };
  showTimestamps?: boolean;
}

export function FactCheckDisplayPublic({
  factCheck,
}: FactCheckDisplayPublicProps) {
  // Show loading state
  if (factCheck.status === "processing") {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-500 mx-auto mb-3" />
          <p className="text-gray-600">Processing fact check...</p>
        </div>
      </div>
    );
  }

  // Show pending state
  if (factCheck.status === "pending") {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <p className="text-gray-600">Fact check pending...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (factCheck.status === "failed") {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
          <div>
            <p className="font-medium text-red-900">Fact check failed</p>
            {factCheck.error_message && (
              <p className="text-sm text-red-700 mt-1">
                {factCheck.error_message}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Completed state - main display
  if (factCheck.status === "completed" && factCheck.body) {
    return (
      <div className="space-y-6">
        {/* Claims Table - Display above the fact check body */}
        {factCheck.claims && factCheck.claims.length > 0 && (
          <ClaimsTable claims={factCheck.claims} />
        )}

        {/* Main Content */}
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 bg-white border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              Fact Check Analysis
            </h3>
          </div>
          <div className="p-6 prose prose-base max-w-none [&>h1]:text-xl [&>h1]:font-bold [&>h1]:text-gray-900 [&>h1]:mt-6 [&>h1]:mb-3 [&>h2]:text-lg [&>h2]:font-bold [&>h2]:text-gray-900 [&>h2]:mt-5 [&>h2]:mb-3 [&>h3]:text-base [&>h3]:font-semibold [&>h3]:text-gray-800 [&>h3]:mt-4 [&>h3]:mb-2 [&>p]:text-gray-700 [&>p]:leading-relaxed [&>p]:my-3 [&>ul]:list-disc [&>ul]:pl-6 [&>ul]:my-3 [&>ul]:space-y-2 [&>ul>li]:text-gray-700 [&>ul>li]:leading-relaxed [&>ol]:list-decimal [&>ol]:pl-6 [&>ol]:my-3 [&>ol]:space-y-2 [&>ol>li]:text-gray-700 [&>ol>li]:leading-relaxed [&_a]:text-blue-600 [&_a]:underline [&_a:hover]:text-blue-800 [&>blockquote]:border-l-4 [&>blockquote]:border-gray-300 [&>blockquote]:pl-4 [&>blockquote]:italic [&>blockquote]:text-gray-600 [&>h1:first-child]:mt-0 [&>h2:first-child]:mt-0 [&>h3:first-child]:mt-0 [&>p:first-child]:mt-0">
            <ReactMarkdown>{factCheck.body}</ReactMarkdown>
          </div>
        </div>
      </div>
    );
  }

  // Fallback for unexpected states
  return (
    <div className="text-center py-12 text-gray-500">
      No fact check content available
    </div>
  );
}
