"use client";

import { useParams, notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { usePostById } from "@/hooks/use-api";
import { useFactCheckPoll } from "@/hooks/use-fact-check-poll";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FactCheckStream } from "@/components/fact-check-stream";
import { getVerdictColorClass } from "@/lib/verdict";

export default function FactCheckPage() {
  const params = useParams();
  const postUid = params.post_uid as string;
  const factCheckerSlug = params.fact_checker_slug as string;

  // Fetch post details
  const {
    data: post,
    isLoading: postLoading,
    error: postError,
  } = usePostById(postUid);

  // Use polling hook for fact check
  const {
    factCheckId,
    status,
    updates,
    verdict,
    confidence,
    body,
    error,
    isComplete,
    isProcessing,
  } = useFactCheckPoll(postUid, factCheckerSlug, true);

  if (postLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (postError || !post) {
    notFound();
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Navigation */}
        <div className="flex items-center justify-between">
          <Link href={`/posts/${postUid}/manage`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Manage
            </Button>
          </Link>
          <h1 className="text-2xl font-bold">Fact Check: {factCheckerSlug}</h1>
        </div>

        {/* Post Info */}
        <Card>
          <CardHeader>
            <CardTitle>Post Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm text-gray-600">Post ID: {postUid}</p>
              <p className="text-sm text-gray-600">
                Author: @{post.author_handle}
              </p>
              <div className="mt-4 p-4 bg-gray-50 rounded">
                <p className="text-sm">{post.text}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Fact Check Content */}
        <Card>
          <CardHeader>
            <CardTitle>
              {isComplete
                ? "Fact Check Complete"
                : isProcessing
                ? "Fact Check in Progress..."
                : status === "failed"
                ? "Fact Check Failed"
                : "Initializing..."}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {error ? (
              <div className="text-red-600">
                <p className="font-semibold">Error:</p>
                <p className="text-sm">{error}</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Show processing status */}
                {isProcessing && (
                  <div className="text-sm text-gray-600">
                    <p>Status: {status}</p>
                    {factCheckId && <p>Fact Check ID: {factCheckId}</p>}
                  </div>
                )}

                {/* Show the streaming updates if we have them */}
                {updates.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="font-semibold text-lg">Analysis Process</h3>
                    <FactCheckStream
                      updates={updates}
                      isProcessing={isProcessing}
                    />
                  </div>
                )}

                {/* Show the final result if complete */}
                {isComplete && body && (
                  <>
                    <div className="pt-4 border-t">
                      <h3 className="font-semibold text-lg mb-3">
                        Final Result
                      </h3>
                      <div className="space-y-2">
                        <div className="flex items-center gap-4">
                          <span className="font-semibold">Verdict:</span>
                          <span
                            className={`px-2 py-1 rounded text-sm ${getVerdictColorClass(verdict)}`}
                          >
                            {verdict}
                          </span>
                          {confidence !== undefined && (
                            <span className="text-sm text-gray-600">
                              ({Math.round(confidence * 100)}% confidence)
                            </span>
                          )}
                        </div>
                        <div className="mt-4">
                          <h4 className="font-semibold mb-2">Fact Check Result:</h4>
                          <div className="prose prose-sm max-w-none bg-gray-50 rounded-lg p-4 [&>h1]:font-bold [&>h1]:text-lg [&>h1]:mt-4 [&>h1]:mb-2 [&>h2]:font-bold [&>h2]:text-lg [&>h2]:mt-4 [&>h2]:mb-2 [&>h3]:font-semibold [&>h3]:text-base [&>h3]:mt-3 [&>h3]:mb-1 [&>p]:my-2 [&>ul]:my-2 [&>ul]:list-disc [&>ul]:pl-6 [&>ul>li]:my-1 [&>ol]:list-decimal [&>ol]:pl-6 [&>ol>li]:my-1 [&_a]:text-blue-600 [&_a]:underline [&_a:hover]:text-blue-800">
                            <ReactMarkdown>{body}</ReactMarkdown>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="pt-4 border-t">
                      <Link href={`/posts/${postUid}/manage`}>
                        <Button variant="outline" size="sm">
                          Back to Manage
                        </Button>
                      </Link>
                    </div>
                  </>
                )}

                {/* Show loading message if no updates yet */}
                {!isComplete &&
                  !error &&
                  updates.length === 0 &&
                  isProcessing && (
                    <div className="text-sm text-gray-600">
                      <p>
                        Processing fact check... This may take a few minutes.
                      </p>
                    </div>
                  )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
