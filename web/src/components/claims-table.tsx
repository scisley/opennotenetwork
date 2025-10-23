"use client";

import { CheckCircle2, XCircle, AlertTriangle, HelpCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Claim {
  claim: string;
  accuracy: string;
  reason: string;
}

interface ClaimsTableProps {
  claims: Claim[];
}

function getAccuracyConfig(accuracy: string) {
  const normalized = accuracy.toLowerCase();
  switch (normalized) {
    case "true":
    case "accurate":
      return {
        icon: <CheckCircle2 className="h-5 w-5 text-green-600" />,
        label: "Accurate",
        textColor: "text-green-700",
      };
    case "false":
    case "inaccurate":
      return {
        icon: <XCircle className="h-5 w-5 text-red-600" />,
        label: "Inaccurate",
        textColor: "text-red-700",
      };
    case "misleading":
    case "mixed":
      return {
        icon: <AlertTriangle className="h-5 w-5 text-amber-600" />,
        label: "Mixed",
        textColor: "text-amber-700",
      };
    case "unverified":
    case "unable_to_verify":
      return {
        icon: <HelpCircle className="h-5 w-5 text-gray-500" />,
        label: "Unverified",
        textColor: "text-gray-600",
      };
    default:
      return {
        icon: <HelpCircle className="h-5 w-5 text-gray-500" />,
        label: accuracy,
        textColor: "text-gray-600",
      };
  }
}

export function ClaimsTable({ claims }: ClaimsTableProps) {
  if (!claims || claims.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 bg-white border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Claims Analysis</h3>
        <p className="text-sm text-gray-600 mt-1">
          Individual claims identified and fact-checked from the post
        </p>
      </div>

      <div className="p-6">
        {claims.map((claim, index) => {
          const config = getAccuracyConfig(claim.accuracy);
          return (
            <div key={index}>
              <div className="flex gap-3 py-4">
                {/* Status Icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {config.icon}
                </div>

                {/* Content */}
                <div className="flex-grow space-y-2">
                  {/* Claim Text */}
                  <div className="text-sm font-medium text-gray-900 leading-relaxed">
                    <span className="font-semibold">Claim:</span> {claim.claim}
                  </div>

                  {/* Summary/Reason */}
                  <div className="text-sm text-gray-600 leading-relaxed prose prose-sm max-w-none [&_a]:text-blue-600 [&_a]:underline [&_a:hover]:text-blue-800 [&_a]:cursor-pointer [&_p]:m-0">
                    <ReactMarkdown
                      components={{
                        a: ({ node, ...props }) => (
                          <a
                            {...props}
                            target="_blank"
                            rel="noopener noreferrer"
                          />
                        ),
                      }}
                    >
                      {claim.reason}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
              {index < claims.length - 1 && (
                <hr className="border-gray-200" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}